"""The e1e75b94 token's isOpen(): a storage flag (slot 5) OR block.timestamp >= an open time compiled into the code. Output: s11d_token.out."""
from common import *
import s07_traits as S
F = sorted([r for r in S.rows.values() if r["sel"] == "0xe1e75b94"], key=lambda r: r["b"])
c = rpc.call("eth_getCode", [F[-1]["tok"], "latest"]); b = bytes.fromhex(c[2:])
N = {0x42: "TIMESTAMP", 0x54: "SLOAD", 0x56: "JUMP", 0x57: "JUMPI", 0x5b: "JUMPDEST", 0x15: "ISZERO", 0x10: "LT", 0x16: "AND", 0x80: "DUP1", 0x90: "SWAP1", 0x50: "POP"}
I = []; i = 0
while i < len(b):
    o = b[i]; n = o - 0x5f if 0x60 <= o <= 0x7f else 0; I.append((i, N.get(o, ("PUSH%d" % n) if n else hex(o)), b[i + 1:i + 1 + n].hex())); i += 1 + n
k = next(k for k, x in enumerate(I) if x[1] == "PUSH4" and x[2] == "47535d7b")
print("selectors:", [a for p, nm, a in I if nm == "PUSH4"]); print("isOpen dispatch ->", I[k + 2][2])
j = next(m for m, x in enumerate(I) if x[0] == 0x854)
print("isOpen body (0x0854):"); [print("  ", x) for x in I[j:j + 20]]
