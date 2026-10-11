"""eth_call (state-override code) that returns, per address: exact code hash, size, mask32 hash (PUSH32 operands zeroed, CBOR metadata
stripped) and skeleton hash (opcodes only, PUSH operands dropped, metadata stripped). Matches lib2.mask32/skeleton (checked on samples)."""
from lib2 import *

OPS = {'ADD': 0x01, 'MUL': 0x02, 'SUB': 0x03, 'LT': 0x10, 'EQ': 0x14, 'ISZERO': 0x15, 'SHR': 0x1c, 'KECCAK': 0x20, 'CALLDATALOAD': 0x35,
       'CALLDATASIZE': 0x36, 'EXTCODESIZE': 0x3b, 'EXTCODECOPY': 0x3c, 'EXTCODEHASH': 0x3f, 'MLOAD': 0x51, 'MSTORE': 0x52, 'MSTORE8': 0x53,
       'JUMP': 0x56, 'JUMPI': 0x57, 'JUMPDEST': 0x5b, 'RETURN': 0xf3, 'SWAP1': 0x90}
V = {n: 0xF000 + 32 * i for i, n in enumerate(["K", "ADDR", "SIZE", "N", "ML", "I", "J", "OP"])}
CODE, SKEL = 0x10000, 0x30000


def assemble(prog):
    out = []; labels = {}; fix = []
    def push(v):
        if v == 0: out.append(0x5f); return                          # PUSH0
        b = v.to_bytes((v.bit_length() + 7) // 8, "big"); out.append(0x5f + len(b)); out.extend(b)
    for t in prog:
        if isinstance(t, tuple):
            k, v = t
            if k == "push": push(v)
            elif k == "load": push(V[v]); out.append(OPS["MLOAD"])
            elif k == "store": push(V[v]); out.append(OPS["MSTORE"])
            elif k == "label": labels[v] = len(out); out.append(OPS["JUMPDEST"])
            elif k in ("jump", "jumpi"):
                out.append(0x61); fix.append((len(out), v)); out.extend(b"\0\0"); out.append(OPS["JUMP" if k == "jump" else "JUMPI"])
        else: out.append(OPS[t])
    for pos, lab in fix: out[pos:pos + 2] = labels[lab].to_bytes(2, "big")
    return "0x" + bytes(out).hex()


P = lambda v: ("push", v); L = lambda v: ("load", v); S = lambda v: ("store", v)
PROG = [P(0), S("K"), ("label", "LOOPK"),
        "CALLDATASIZE", L("K"), P(32), "MUL", "LT", "ISZERO", ("jumpi", "END"),
        L("K"), P(32), "MUL", "CALLDATALOAD", S("ADDR"),
        L("ADDR"), "EXTCODESIZE", S("SIZE"),
        L("SIZE"), P(0), P(CODE), L("ADDR"), "EXTCODECOPY",
        L("ADDR"), "EXTCODEHASH", L("K"), P(128), "MUL", "MSTORE",
        L("SIZE"), L("K"), P(128), "MUL", P(32), "ADD", "MSTORE",
        L("SIZE"), S("N"),
        L("SIZE"), P(2), "LT", "ISZERO", ("jumpi", "NOSTRIP"),
        P(2), L("SIZE"), "SUB", P(CODE), "ADD", "MLOAD", P(240), "SHR", S("ML"),
        L("ML"), "ISZERO", ("jumpi", "NOSTRIP"),
        P(2), L("SIZE"), "SUB", L("ML"), "LT", "ISZERO", ("jumpi", "NOSTRIP"),
        L("ML"), P(2), L("SIZE"), "SUB", "SUB", P(CODE), "ADD", "MLOAD", P(248), "SHR",
        P(0xa1), "SWAP1", "SUB", P(3), "SWAP1", "LT", "ISZERO", ("jumpi", "NOSTRIP"),
        L("ML"), P(2), L("SIZE"), "SUB", "SUB", S("N"),
        ("label", "NOSTRIP"), P(0), S("I"), P(0), S("J"),
        ("label", "LOOPI"),
        L("N"), L("I"), "LT", "ISZERO", ("jumpi", "DONEI"),
        L("I"), P(CODE), "ADD", "MLOAD", P(248), "SHR", S("OP"),
        L("OP"), L("J"), P(SKEL), "ADD", "MSTORE8",
        L("J"), P(1), "ADD", S("J"),
        P(0x60), L("OP"), "SUB", P(32), "SWAP1", "LT", "ISZERO", ("jumpi", "NOPUSH"),
        L("OP"), P(0x7f), "EQ", "ISZERO", ("jumpi", "NOZERO"),
        P(0), L("I"), P(CODE), "ADD", P(1), "ADD", "MSTORE",
        ("label", "NOZERO"),
        P(0x5f), L("OP"), "SUB", L("I"), "ADD", S("I"),
        ("label", "NOPUSH"),
        L("I"), P(1), "ADD", S("I"), ("jump", "LOOPI"),
        ("label", "DONEI"),
        L("N"), P(CODE), "KECCAK", L("K"), P(128), "MUL", P(64), "ADD", "MSTORE",
        L("J"), P(SKEL), "KECCAK", L("K"), P(128), "MUL", P(96), "ADD", "MSTORE",
        L("K"), P(1), "ADD", S("K"), ("jump", "LOOPK"),
        ("label", "END"), L("K"), P(128), "MUL", P(0), "RETURN"]
HCODE = assemble(PROG)
HADDR = "0x00000000000000000000000000000000000c0de2"


def mask32(code_hex):
    b = bytes.fromhex(code_hex[2:] if code_hex.startswith("0x") else code_hex)
    if not b: return None
    if len(b) > 2:
        ml = int.from_bytes(b[-2:], "big")
        if 0 < ml < len(b) - 2 and b[-2 - ml] in (0xa1, 0xa2, 0xa3): b = b[:-2 - ml]
    out = bytearray(b); i = 0; n = len(b)
    while i < n:
        op = b[i]
        if op == 0x7f: out[i + 1:i + 33] = bytes(min(32, n - i - 1))
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return keccak(bytes(out)).hex()


def code_hashes(addrs, per_call=40, gas=45_000_000):
    """addr -> {"h": exact, "size", "m": mask32, "sk": skeleton} (None hashes for empty code)"""
    out = {}
    calls = []
    for i in range(0, len(addrs), per_call):
        ch = addrs[i:i + per_call]
        calls.append((ch, ("eth_call", [{"to": HADDR, "data": "0x" + "".join("0" * 24 + a[2:] for a in ch), "gas": hex(gas)}, "latest", {HADDR: {"code": HCODE}}])))
    for j in range(0, len(calls), 5):
        grp = calls[j:j + 5]
        res = batch([c for _, c in grp], size=5)
        for (ch, _), r in zip(grp, res):
            if r is None:
                if len(ch) > 1:                                     # out of gas or an error: split
                    out.update(code_hashes(ch[:len(ch) // 2], per_call, gas)); out.update(code_hashes(ch[len(ch) // 2:], per_call, gas))
                else: out[ch[0]] = None
                continue
            for k, a in enumerate(ch):
                w = r[2 + 256 * k: 2 + 256 * (k + 1)]
                sz = int(w[64:128], 16)
                out[a] = {"h": w[:64] if sz else None, "size": sz, "m": w[128:192] if sz else None, "sk": w[192:256] if sz else None}
    return out
