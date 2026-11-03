#!/usr/bin/env python3
"""minievm.py: a small EVM interpreter for one contract that makes no external calls (a token's transfer logic), with a trace.

Runs the contract's real runtime code (eth_getCode) against its real storage (eth_getStorageAt at a block, read on demand and cached),
with every environment value set by the caller: msg.sender, tx.origin, tx.gasprice, block.coinbase, block.timestamp, block.number, and
storage overrides. Records each storage read and write (a mapping slot is shown as map[base][key] from the SHA3 that made it), each
conditional jump taken or not, each log and the revert data. Raises on an opcode it does not model (CALL and the like): the caller then
knows the path left the contract. Read-only (RPC reads only)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eth_utils import keccak
import hlib as H

M256 = (1 << 256) - 1


def s256(x):
    return x - (1 << 256) if x >> 255 else x


class Revert(Exception):
    pass


class EVM:
    def __init__(self, ch, address, block="latest", code=None):
        self.url = H.CH[ch]["rpc"]; self.address = address.lower(); self.block = block
        self.code = bytes.fromhex((code or H.rpc(self.url, "eth_getCode", [self.address, block]))[2:])
        self.jumpdests = set(); i = 0
        while i < len(self.code):
            op = self.code[i]
            if op == 0x5b:
                self.jumpdests.add(i)
            i += 1 + (op - 0x5f if 0x60 <= op <= 0x7f else 0)
        self.storage = {}; self.preimage = {}

    def sload_chain(self, slot):
        if slot not in self.storage:
            self.storage[slot] = int(H.rpc(self.url, "eth_getStorageAt", [self.address, hex(slot), self.block]), 16)
        return self.storage[slot]

    def slot_name(self, slot):
        if slot in self.preimage:
            key, base = self.preimage[slot]
            return f"map[{self.slot_name(base)}][{hex(key) if key > 2 ** 64 else key}]"
        return str(slot) if slot < 2 ** 64 else hex(slot)[:12] + "…"

    def run(self, calldata, sender, origin=None, gasprice=0, coinbase=0, timestamp=0, number=0, value=0, overrides=None, trace=True, max_steps=200000):
        st = dict(self.storage); st.update(overrides or {})
        saved = self.storage; self.storage = st
        stack, mem, pc, steps = [], bytearray(), 0, 0
        cd = bytes.fromhex(calldata[2:] if calldata.startswith("0x") else calldata)
        ev = {"sloads": [], "sstores": [], "jumps": [], "logs": [], "env": [], "result": None, "revert": None}
        tstore = {}

        def mext(off, n):
            if n and off + n > len(mem):
                mem.extend(b"\0" * (((off + n + 31) // 32) * 32 - len(mem)))

        try:
            while True:
                steps += 1
                if steps > max_steps:
                    raise RuntimeError("step limit")
                if pc >= len(self.code):
                    ev["result"] = b""; break
                op = self.code[pc]
                if 0x60 <= op <= 0x7f:
                    n = op - 0x5f; stack.append(int.from_bytes(self.code[pc + 1:pc + 1 + n].ljust(n, b"\0"), "big")); pc += 1 + n; continue
                if op == 0x5f:
                    stack.append(0)
                elif 0x80 <= op <= 0x8f:
                    stack.append(stack[-(op - 0x7f)])
                elif 0x90 <= op <= 0x9f:
                    k = op - 0x8f; stack[-1], stack[-1 - k] = stack[-1 - k], stack[-1]
                elif op == 0x00:
                    ev["result"] = b""; break
                elif op == 0x01:
                    a, b = stack.pop(), stack.pop(); stack.append((a + b) & M256)
                elif op == 0x02:
                    a, b = stack.pop(), stack.pop(); stack.append((a * b) & M256)
                elif op == 0x03:
                    a, b = stack.pop(), stack.pop(); stack.append((a - b) & M256)
                elif op == 0x04:
                    a, b = stack.pop(), stack.pop(); stack.append(a // b if b else 0)
                elif op == 0x05:
                    a, b = s256(stack.pop()), s256(stack.pop()); stack.append((abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)) & M256 if b else 0)
                elif op == 0x06:
                    a, b = stack.pop(), stack.pop(); stack.append(a % b if b else 0)
                elif op == 0x07:
                    a, b = s256(stack.pop()), s256(stack.pop()); stack.append(((abs(a) % abs(b)) * (-1 if a < 0 else 1)) & M256 if b else 0)
                elif op == 0x08:
                    a, b, n = stack.pop(), stack.pop(), stack.pop(); stack.append((a + b) % n if n else 0)
                elif op == 0x09:
                    a, b, n = stack.pop(), stack.pop(), stack.pop(); stack.append((a * b) % n if n else 0)
                elif op == 0x0a:
                    a, b = stack.pop(), stack.pop(); stack.append(pow(a, b, 1 << 256))
                elif op == 0x0b:
                    b, x = stack.pop(), stack.pop()
                    if b < 31:
                        bit = b * 8 + 7; m = (1 << bit) - 1
                        x = (x | (M256 ^ m)) if (x >> bit) & 1 else (x & m)
                    stack.append(x & M256)
                elif op == 0x10:
                    a, b = stack.pop(), stack.pop(); stack.append(int(a < b))
                elif op == 0x11:
                    a, b = stack.pop(), stack.pop(); stack.append(int(a > b))
                elif op == 0x12:
                    a, b = s256(stack.pop()), s256(stack.pop()); stack.append(int(a < b))
                elif op == 0x13:
                    a, b = s256(stack.pop()), s256(stack.pop()); stack.append(int(a > b))
                elif op == 0x14:
                    a, b = stack.pop(), stack.pop(); stack.append(int(a == b))
                elif op == 0x15:
                    stack.append(int(stack.pop() == 0))
                elif op == 0x16:
                    a, b = stack.pop(), stack.pop(); stack.append(a & b)
                elif op == 0x17:
                    a, b = stack.pop(), stack.pop(); stack.append(a | b)
                elif op == 0x18:
                    a, b = stack.pop(), stack.pop(); stack.append(a ^ b)
                elif op == 0x19:
                    stack.append(M256 ^ stack.pop())
                elif op == 0x1a:
                    i, x = stack.pop(), stack.pop(); stack.append((x >> (8 * (31 - i))) & 0xff if i < 32 else 0)
                elif op == 0x1b:
                    s, x = stack.pop(), stack.pop(); stack.append((x << s) & M256 if s < 256 else 0)
                elif op == 0x1c:
                    s, x = stack.pop(), stack.pop(); stack.append(x >> s if s < 256 else 0)
                elif op == 0x1d:
                    s, x = stack.pop(), s256(stack.pop()); stack.append((x >> s if s < 256 else (0 if x >= 0 else -1)) & M256)
                elif op == 0x20:
                    off, n = stack.pop(), stack.pop(); mext(off, n); data = bytes(mem[off:off + n]); h = int.from_bytes(keccak(data), "big")
                    if n == 64:
                        self.preimage[h] = (int.from_bytes(data[:32], "big"), int.from_bytes(data[32:], "big"))
                    stack.append(h)
                elif op == 0x30:
                    stack.append(int(self.address, 16))
                elif op == 0x32:
                    stack.append(int(origin or sender, 16)); ev["env"].append((pc, "ORIGIN"))
                elif op == 0x33:
                    stack.append(int(sender, 16))
                elif op == 0x34:
                    stack.append(value)
                elif op == 0x35:
                    off = stack.pop(); stack.append(int.from_bytes(cd[off:off + 32].ljust(32, b"\0"), "big") if off < len(cd) else 0)
                elif op == 0x36:
                    stack.append(len(cd))
                elif op == 0x37:
                    m, off, n = stack.pop(), stack.pop(), stack.pop(); mext(m, n); mem[m:m + n] = cd[off:off + n].ljust(n, b"\0")
                elif op == 0x38:
                    stack.append(len(self.code))
                elif op == 0x39:
                    m, off, n = stack.pop(), stack.pop(), stack.pop(); mext(m, n); mem[m:m + n] = self.code[off:off + n].ljust(n, b"\0")
                elif op == 0x3a:
                    stack.append(gasprice); ev["env"].append((pc, "GASPRICE"))
                elif op == 0x3d:
                    stack.append(0)
                elif op == 0x41:
                    stack.append(int(coinbase, 16) if isinstance(coinbase, str) else coinbase); ev["env"].append((pc, "COINBASE"))
                elif op == 0x42:
                    stack.append(timestamp); ev["env"].append((pc, "TIMESTAMP"))
                elif op == 0x43:
                    stack.append(number); ev["env"].append((pc, "NUMBER"))
                elif op == 0x46:
                    stack.append(56)
                elif op == 0x47:
                    stack.append(0)
                elif op == 0x48:
                    stack.append(0)
                elif op == 0x50:
                    stack.pop()
                elif op == 0x51:
                    off = stack.pop(); mext(off, 32); stack.append(int.from_bytes(mem[off:off + 32], "big"))
                elif op == 0x52:
                    off, v = stack.pop(), stack.pop(); mext(off, 32); mem[off:off + 32] = v.to_bytes(32, "big")
                elif op == 0x53:
                    off, v = stack.pop(), stack.pop(); mext(off, 1); mem[off] = v & 0xff
                elif op == 0x54:
                    slot = stack.pop(); v = self.sload_chain(slot); stack.append(v); ev["sloads"].append((pc, self.slot_name(slot), v))
                elif op == 0x55:
                    slot, v = stack.pop(), stack.pop(); self.storage[slot] = v; ev["sstores"].append((pc, self.slot_name(slot), v))
                elif op == 0x56:
                    d = stack.pop()
                    if d not in self.jumpdests:
                        raise Revert("bad jump")
                    pc = d; continue
                elif op == 0x57:
                    d, c = stack.pop(), stack.pop()
                    ev["jumps"].append((pc, d, bool(c)))
                    if c:
                        if d not in self.jumpdests:
                            raise Revert("bad jump")
                        pc = d; continue
                elif op == 0x58:
                    stack.append(pc)
                elif op == 0x59:
                    stack.append(len(mem))
                elif op == 0x5a:
                    stack.append(10 ** 7)
                elif op == 0x5b:
                    pass
                elif op == 0x5c:
                    stack.append(tstore.get(stack.pop(), 0))
                elif op == 0x5d:
                    k, v = stack.pop(), stack.pop(); tstore[k] = v
                elif op == 0x5e:
                    dst, src, n = stack.pop(), stack.pop(), stack.pop(); mext(max(dst, src), n); mem[dst:dst + n] = bytes(mem[src:src + n])
                elif 0xa0 <= op <= 0xa4:
                    off, n = stack.pop(), stack.pop(); topics = [stack.pop() for _ in range(op - 0xa0)]; mext(off, n)
                    ev["logs"].append(([hex(t) for t in topics], bytes(mem[off:off + n]).hex()))
                elif op == 0xf3:
                    off, n = stack.pop(), stack.pop(); mext(off, n); ev["result"] = bytes(mem[off:off + n]); break
                elif op == 0xfd:
                    off, n = stack.pop(), stack.pop(); mext(off, n); ev["revert"] = bytes(mem[off:off + n]); break
                elif op == 0xfe:
                    ev["revert"] = b"INVALID"; break
                else:
                    raise RuntimeError(f"opcode 0x{op:02x} at pc {pc} not modelled (the path leaves the contract)")
                pc += 1
        finally:
            self.storage = saved if trace else saved
        return ev
