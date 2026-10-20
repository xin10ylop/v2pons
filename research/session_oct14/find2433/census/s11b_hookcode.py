"""Code of the e1e75b94 family's hooks / launch contracts / tokens and of the buyers W9/W9b (latest state): size, keccak, balance, nonce, and
gate-relevant opcode counts; the hook's disassembly around ORIGIN (tx.origin passed to a call of token.isOpen()/allowlist). Output: s11b_hookcode.out."""
from common import *
import collections
import s07_traits as S
F = sorted([r for r in S.rows.values() if r["sel"] == "0xe1e75b94"], key=lambda r: r["b"])
addrs = []
for r in (F[0], F[1], F[-1]): addrs += [("hook", r["hook"]), ("launch contract", r["to"]), ("token", r["tok"])]
addrs += [("W9", "0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"), ("W9b", "0x35eb8c43c7f8da87eb21749787c92cfab6cdf751")]
codes = rpc.batch("eth_getCode", [[a, "latest"] for _, a in addrs], n=10)
bals = rpc.batch("eth_getBalance", [[a, "latest"] for _, a in addrs], n=10)
ncs = rpc.batch("eth_getTransactionCount", [[a, "latest"] for _, a in addrs], n=10)
def ins(b):
    i = 0; out = []
    while i < len(b):
        o = b[i]; n = o - 0x5f if 0x60 <= o <= 0x7f else 0; out.append((i, o, b[i + 1:i + 1 + n].hex())); i += 1 + n
    return out
for (k, a), c, bal, nc in zip(addrs, codes, bals, ncs):
    b = bytes.fromhex(c[2:]) if c and c != "0x" else b""
    oc = collections.Counter(o for _, o, _ in ins(b))
    print("%-16s %s size %5d keccak %s bal %.5f nonce %d  ORIGIN %d CALLER %d TIMESTAMP %d" % (k, a, len(b), ("0x" + keccak(b).hex()[:12]) if b else "-", int(bal, 16) / 1e18, int(nc, 16), oc.get(0x32, 0), oc.get(0x33, 0), oc.get(0x42, 0)))
b = bytes.fromhex(codes[0][2:]); I = ins(b)
print("\nhook PUSH4 constants (dispatcher + external calls):", [a for _, o, a in I if o == 0x63], "(0x575e24b4 = beforeSwap, 0x47535d7b = isOpen(), 0xe09f0331 = the revert error)")
