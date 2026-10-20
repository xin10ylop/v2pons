"""(1) tok:0f34e3b5: does the operator pull after a stranger (non-fleet) buy? Pools with a non-fleet buy >= 0.001 ETH before the pull
(fleet = 7ff36ab5/228-byte single-use wallets; the dust bots 0xe71a69f4.., 0xe9d83e95.. and buys < 0.001 ignored): pull rate and
pull delay after it, vs pools without. (2) the line as the feed sees it: PositionManager-V3 0x73991a25 multicall of 836 bytes, fee 100,
value 0 (lc 0a493d1a|ac9650d8 strict key) — the cap grid on all those launches, whatever their token template."""
import sys, os, pickle, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s15_honest as H
from replay import *
FP = H.FP; E = H.E; T = H.T
rs = FP["tok:0f34e3b5"]
with_s, without = [], []
for r in rs:
    o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]; stranger = None
    pull = r["first_pull_off"]
    for e in o["ev"]:
        if e[0] != "s": continue
        off = e[1] - lb
        if pull is not None and off >= pull: break
        qin, tout = (e[6], e[9]) if qs == 0 else (e[7], e[8])
        if not (qin >= 1e15 and tout > 0): continue
        t = T.get(e[-1])
        if not t: continue
        if t["selector"] == "7ff36ab5" and t["calldata_len"] == 228: continue
        stranger = (off, qin / 1e18, t["from"][:10], t["to"][:10], t["selector"]); break
    (with_s if stranger else without).append((r, stranger))
def pr(lab, xs):
    pl = [r for r, s in xs if r["n_pulls"]]
    print(f"  {lab}: pools {len(xs)} pulled {len(pl)} ({len(pl)/max(1,len(xs)):.2f})")
print("(1) tok:0f34e3b5 stranger buys (fetched txs only)")
pr("with a non-fleet buy >= 0.001 ETH before the pull", with_s); pr("without", without)
d = [r["first_pull_off"] - s[0] for r, s in with_s if r["n_pulls"]]
print("  pull delay after the stranger's buy (blocks) sorted:", sorted(d)[:30])
print("  strangers:", Counter((s[3], s[4]) for r, s in with_s).most_common(6))
print("\n(2) strict feed key: 0x73991a25 multicall ac9650d8, 836 bytes, fee 100, value 0")
L = [r for r in H.R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
print("  launches", len(L), "token templates", Counter(r["fam"]["tok"][:8] for r in L).most_common(6))
for C in (80, 100, 120):
    for k in (1, 20):
        xs = []
        for r in L:
            if r["liq_off"] is None: continue
            a, b, drop = H.plan(r, k, C)
            x = replay(r, E[r["pool"]], a, b, H.Q, drop) if r["pool"] in E else {"ok": False}
            if x["ok"]: x["day"] = H.day(r); xs.append(x)
        print(H.summarize(f"k={k} cap={C}", xs, len(L)))
