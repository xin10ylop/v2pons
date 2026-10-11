"""Exit-cap grid (every launch traded, sell k blocks after the first real buy at/after our buy, else at the cap) for the V3 crowd line
(tok:d4e7eae4 V3 part), long holds on tok:70adce63, the 0f34e3b5 follow (buy 2 blocks after the fleet's first buy, sell into the next
real buy) at several stakes, and pull timing in d4e7eae4 pools without a real buy."""
import sys, os, pickle, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
import s15_honest as H
FP = H.FP; E = H.E
def run(rs, fn, qq=0.0058):
    xs = []
    for r in rs:
        if r["liq_off"] is None: continue
        p = fn(r)
        if p is None: continue
        a, b, drop = p
        x = replay(r, E[r["pool"]], a, b, qq, drop)
        if x["ok"]: x["day"] = H.day(r); xs.append(x)
    return xs
d4 = [r for r in FP["tok:d4e7eae4"] if r["dex"] == "v3"]
print("### tok:d4e7eae4 V3: cap grid (front a=liq+2)")
for C in (60, 80, 100, 120, 150, 200):
    for k in (1, 5, 20):
        print(H.summarize(f"k={k} cap={C}", run(d4, lambda r: H.plan(r, k, C)), len(d4)))
nof = [r for r in d4 if not r["frb"]]
pl = [r["first_pull_off"] for r in nof if r["n_pulls"]]
print(f"  pools without a real buy: {len(nof)}; pulled {len(pl)} at p10/50/90 {sorted(pl)[len(pl)//10] if pl else None}/{sorted(pl)[len(pl)//2] if pl else None}/{sorted(pl)[9*len(pl)//10] if pl else None}")
wf = [r for r in d4 if r["frb"]]
late = [r for r in wf if r["frb"]["off"] > 100]
print(f"  pools with a real buy: {len(wf)}; real buy after +100: {len(late)}; of those pulled before +100: {sum(1 for r in late if r['n_pulls'] and r['first_pull_off'] <= 100)}")
print("\n### tok:70adce63 long holds (front a=2, fixed b)")
r70 = FP["tok:70adce63"]
for b in (300, 600, 1000, 2000, 2900):
    print(H.summarize(f"b={b}", run(r70, lambda r, b=b: (2, b, None)), len(r70)))
print("\n### tok:0f34e3b5 follow: buy at frb+2, sell into the next real buy +1 (cap a+300), stakes")
r0 = FP["tok:0f34e3b5"]
def fol(r, C=300):
    if not r["frb"]: return None
    a = r["frb"]["off"] + 2
    nb = [off for off, dq, e in H.buys(r) if off >= a and dq >= 5e15]
    return (a, nb[0] + 1 if nb and nb[0] + 1 <= a + C else a + C, None)
for qq in (0.0058, 0.02, 0.05, 0.1):
    print(H.summarize(f"q={qq}", run(r0, fol, qq), len(r0)))
