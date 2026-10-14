"""tiny EVM disassembler + selector/push extraction (read-only analysis helper)"""
import sys
OP = {}
names = """00 STOP 01 ADD 02 MUL 03 SUB 04 DIV 05 SDIV 06 MOD 07 SMOD 08 ADDMOD 09 MULMOD 0a EXP 0b SIGNEXTEND 10 LT 11 GT 12 SLT 13 SGT 14 EQ 15 ISZERO 16 AND 17 OR 18 XOR 19 NOT 1a BYTE 1b SHL 1c SHR 1d SAR 20 KECCAK256 30 ADDRESS 31 BALANCE 32 ORIGIN 33 CALLER 34 CALLVALUE 35 CALLDATALOAD 36 CALLDATASIZE 37 CALLDATACOPY 38 CODESIZE 39 CODECOPY 3a GASPRICE 3b EXTCODESIZE 3c EXTCODECOPY 3d RETURNDATASIZE 3e RETURNDATACOPY 3f EXTCODEHASH 40 BLOCKHASH 41 COINBASE 42 TIMESTAMP 43 NUMBER 44 PREVRANDAO 45 GASLIMIT 46 CHAINID 47 SELFBALANCE 48 BASEFEE 49 BLOBHASH 4a BLOBBASEFEE 50 POP 51 MLOAD 52 MSTORE 53 MSTORE8 54 SLOAD 55 SSTORE 56 JUMP 57 JUMPI 58 PC 59 MSIZE 5a GAS 5b JUMPDEST 5c TLOAD 5d TSTORE 5e MCOPY 5f PUSH0 f0 CREATE f1 CALL f2 CALLCODE f3 RETURN f4 DELEGATECALL f5 CREATE2 fa STATICCALL fd REVERT fe INVALID ff SELFDESTRUCT a0 LOG0 a1 LOG1 a2 LOG2 a3 LOG3 a4 LOG4""".split()
for i in range(0, len(names), 2): OP[int(names[i], 16)] = names[i + 1]
for i in range(32): OP[0x60 + i] = f"PUSH{i+1}"
for i in range(16): OP[0x80 + i] = f"DUP{i+1}"; OP[0x90 + i] = f"SWAP{i+1}"
def dis(h):
    code = bytes.fromhex(h[2:] if h.startswith("0x") else h)
    ins = []; i = 0
    while i < len(code):
        op = code[i]; n = OP.get(op, f"UNK{op:02x}")
        if 0x60 <= op <= 0x7f:
            k = op - 0x5f; ins.append((i, n, code[i + 1:i + 1 + k].hex())); i += 1 + k
        else: ins.append((i, n, None)); i += 1
    return ins
def selectors(ins):
    return [x for j, (a, n, x) in enumerate(ins) if n == "PUSH4" and j + 1 < len(ins) and ins[j + 1][1] in ("EQ",) ]
if __name__ == "__main__":
    ins = dis(open(sys.argv[1]).read().strip())
    open(sys.argv[2], "w").write("\n".join(f"{a:05x} {n} {x or ''}" for a, n, x in ins))
