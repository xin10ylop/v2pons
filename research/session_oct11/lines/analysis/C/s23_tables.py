"""Report helper: launches per calendar day and per 24-h window for the candidate lines, and the last-24-h $/day of each best rule."""
import sys, os, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s15_honest as H
from replay import *
FP = H.FP; E = H.E
L = [r for r in H.R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
lines = {"V3 crowd line (836 B, fee 100)": (L, lambda r: H.plan(r, 20, 80)[:2]),
         "V3 crowd line cap 60": (L, lambda r: H.plan(r, 20, 60)[:2]),
         "lc:0a493d1a|13ead562": (FP["lc:0a493d1a|13ead562"], lambda r: H.plan(r, 1, 60)[:2]),
         "tok:70adce63": (FP["tok:70adce63"], lambda r: (2, r["frb"]["off"] + 1) if r["frb"] else (2, 300)),
         "tok:0f34e3b5 (front, no revert model)": (FP["tok:0f34e3b5"], lambda r: (2, r["frb"]["off"] + 1) if r["frb"] and r["frb"]["off"] >= 2 else (2, 300))}
for name, (rs, fn) in lines.items():
    cal = Counter(r["launch_utc"][5:10] for r in rs); win = Counter(H.day(r) for r in rs)
    xs = []
    for r in rs:
        if r["liq_off"] is None: continue
        a, b = fn(r); x = replay(r, E[r["pool"]], a, b, 0.0058)
        if x["ok"]: x["day"] = H.day(r); xs.append(x)
    d6 = [x for x in xs if x["day"] == 6]
    allr = [x["ret"] for x in xs]
    print(f"{name}: launches {len(rs)}; per calendar day {sorted(cal.items())}; per 24-h window d0..d6 {[win[d] for d in range(7)]}")
    print(f"   rule over all: n {len(xs)} mean {st.mean(allr)*100:+.1f}% $/trade {st.mean([x['usd'] for x in xs]):+.3f} $/day {st.mean([x['usd'] for x in xs])*len(xs)/7:+.1f}")
    if d6: print(f"   last 24 h: n {len(d6)} mean {st.mean([x['ret'] for x in d6])*100:+.1f}% median {st.median([x['ret'] for x in d6])*100:+.1f}% pulled {sum(1 for x in d6 if x['pulled'])} $/day {sum(x['usd'] for x in d6):+.1f}")

# exact worst trade and win share of the V3 crowd line rule (cap 80) and its profit concentration
xs = []
for r in L:
    a, b = H.plan(r, 20, 80)[:2]; x = replay(r, E[r["pool"]], a, b, 0.0058)
    if x["ok"]: xs.append(x)
rets = sorted(x["ret"] for x in xs)
usd = sorted((x["usd"] for x in xs), reverse=True)
print(f"V3 crowd cap 80: worst {rets[0]*100:.3f}%  p10/p90 {rets[len(rets)//10]*100:+.2f}%/{rets[9*len(rets)//10]*100:+.2f}%  share > +1%: {sum(1 for v in rets if v > 0.01)/len(rets):.2f}  top-10% trades' share of PnL {sum(usd[:len(usd)//10])/sum(usd):.2f}")
