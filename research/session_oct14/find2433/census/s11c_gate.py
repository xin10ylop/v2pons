"""Is the e1e75b94 pool open to outsiders while it lives? (eth_call only, latest state; the node has no state for blocks inside a pool's life.)
1) beforeSwap (0x575e24b4) on three hooks from W9, W9b, the launcher, an arbitrary EOA and our relay address (latest state: token now open);
2) token.isOpen() (0x47535d7b) now; 3) the open time compiled into each token (PUSH32 compared with TIMESTAMP in isOpen) vs launch and pull;
4) token.d63a8e11(address) (the allowlist the hook consults while the token is closed). Output: s11c_gate.out."""
import re
from common import *
import s07_traits as S
F = sorted([r for r in S.rows.values() if r["sel"] == "0xe1e75b94"], key=lambda r: r["b"])
W9 = "0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"; W9b = "0x35eb8c43c7f8da87eb21749787c92cfab6cdf751"
OUT1 = "0x1111111111111111111111111111111111111111"; RELAYISH = "0x2abb565300000000000000000000000000000000"
def ea(a): return a[2:].rjust(64, "0")
def ei(x): return format(x % (1 << 256), "064x")
print("== 1) beforeSwap now (the token is open now, so every origin passes)")
for r in (F[0], F[70], F[-1]):
    data = "0x575e24b4" + ea(UR) + ea(r["c0"]) + ea(r["c1"]) + ei(r["fee"]) + ei(r["ts"]) + ea(r["hook"]) + ei(1) + ei(-10**15) + ei(4295128740) + ei(320) + ei(0)
    for who in (W9, W9b, r["frm"], OUT1, RELAYISH):
        try: print(r["hook"][:12], "from", who[:12], "OK", rpc.call("eth_call", [{"from": who, "to": r["hook"], "data": data}, "latest"])[:10])
        except Exception as e: print(r["hook"][:12], "from", who[:12], "REVERT", str(e)[:120])
print("\n== 2) isOpen() now")
for r in (F[0], F[-1]):
    for k, a in (("token", r["tok"]), ("launch contract", r["to"]), ("hook", r["hook"])):
        try: print(k, a[:12], rpc.call("eth_call", [{"to": a, "data": "0x47535d7b"}, "latest"]))
        except Exception as e: print(k, a[:12], "ERR", str(e)[:100])
print("\n== 3) open time in the token code vs launch (pull at ~+30 blocks = ~3 s)")
sample = F[::15][:11]
codes = rpc.batch("eth_getCode", [[r["tok"], "latest"] for r in sample], n=10)
for r, c in zip(sample, codes):
    m = list(re.finditer(r"7f([0-9a-f]{64})42", c[2:])); ot = int(m[0].group(1), 16) if m else None
    pl, _ = S.pulls(S.EV[r["pid"]])
    print(hm(r["t"]), "tok", r["tok"][:12], "open at", hm(ot) if ot else None, "= launch + %.0f s" % (ot - r["t"]) if ot else "", "| pull at +%s blocks" % ((pl[0] - r["b"]) if pl else None))
print("\n== 4) allowlist d63a8e11(address) on two tokens (1 = allowed)")
for r in (F[0], F[-1]):
    for who in (W9, W9b, r["frm"], OUT1, RELAYISH):
        out = rpc.call("eth_call", [{"to": r["tok"], "data": "0xd63a8e11" + ea(who)}, "latest"])
        print(r["tok"][:12], who[:12], int(out, 16))
