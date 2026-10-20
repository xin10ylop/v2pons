"""Final numbers for the report.
(a) the V3 crowd line as the feed sees it (0x73991a25 multicall 836 B, fee 100, value 0): front a=2, sell 20 blocks after the first
    real buy at/after ours, else at the cap (80 / 100); stakes 0.0058..0.2 ETH; per day.
(b) tok:0f34e3b5 with the operator's reaction (a stranger's buy is followed by a pull 77-95 blocks later, s19): follow a = frb+2,
    sell into the next real buy if it lands by a+76, else at a+76; and the same with the reaction ignored.
(c) tok:70adce63 if the reaction pull came 151 blocks after our buy (worst case of s19): front a=2, b=frb+1 only when frb+1 < 153,
    otherwise -100%.
(d) lc:0a493d1a|13ead562: the d6 regime (operator's first buy 0.001 ETH)."""
import sys, os, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s15_honest as H
from replay import *
FP = H.FP; E = H.E
def run(rs, fn, qq=0.0058):
    xs = []
    for r in rs:
        if r["liq_off"] is None: continue
        p = fn(r)
        if p is None: continue
        if p == "loss":
            xs.append({"ok": True, "ret": -1.0, "usd": -qq * ETH_USD - GAS_USD, "pulled": True, "day": H.day(r)}); continue
        a, b = p
        x = replay(r, E[r["pool"]], a, b, qq)
        if x["ok"]: x["day"] = H.day(r); xs.append(x)
    return xs
L = [r for r in H.R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
print(f"(a) V3 crowd line, {len(L)} launches ({len(L)/7:.1f}/day)")
for C in (80, 100):
    for qq in (0.0058, 0.02, 0.05, 0.1, 0.2):
        xs = run(L, lambda r: H.plan(r, 20, C)[:2], qq)
        print(H.summarize(f"cap {C} q={qq}", xs, len(L)))
r0 = FP["tok:0f34e3b5"]
def fol(r, W):
    if not r["frb"]: return None
    a = r["frb"]["off"] + 2
    nb = [off for off, dq, e in H.buys(r) if off >= a and dq >= 5e15]
    return (a, nb[0] + 1 if nb and nb[0] + 1 <= a + W else a + W)
print(f"\n(b) tok:0f34e3b5 follow, {len(r0)} launches")
print(H.summarize("sell into next real buy by a+76 (reaction-safe)", run(r0, lambda r: fol(r, 76)), len(r0)))
print(H.summarize("sell into next real buy by a+300 (reaction ignored)", run(r0, lambda r: fol(r, 300)), len(r0)))
r7 = FP["tok:70adce63"]
print(f"\n(c) tok:70adce63, {len(r7)} launches")
print(H.summarize("front a=2 b=frb+1, reaction ignored", run(r7, lambda r: (2, r["frb"]["off"] + 1) if r["frb"] else (2, 300)), len(r7)))
print(H.summarize("front a=2 b=frb+1, pull 151 blocks after our buy (worst case)", run(r7, lambda r: ((2, r["frb"]["off"] + 1) if r["frb"]["off"] + 1 < 153 else "loss") if r["frb"] else "loss"), len(r7)))
r13 = FP["lc:0a493d1a|13ead562"]
print(f"\n(d) lc:0a493d1a|13ead562, {len(r13)} launches")
print(H.summarize("front a=liq+2, sell first real buy+1 (cap 60)", run(r13, lambda r: H.plan(r, 1, 60)[:2]), len(r13)))
d6 = [r for r in r13 if H.day(r) == 6]
print(H.summarize("same, last 24 h only", run(d6, lambda r: H.plan(r, 1, 60)[:2]), len(d6)))
