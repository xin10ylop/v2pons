"""vbot 2.433: does the pull timing differ in pools where our engine really traded (relay swaps in the events) vs the same days' pools where it
did not? (a direct test of the operator's reaction to us); also the pull offset relative to the bot's first buy"""
from common import *
import numpy as np
rows = {r["pool"]: r for r in load_rows()}
kept = json.load(open(os.path.join(G, "families_kept.json")))
fk = [k for k in kept if k.endswith("|2.4333285")][0]
print(fk)
for d in range(7):
    rs = [rows[p] for p in kept[fk] if day(rows[p]["launch_ts"]) == d]
    for lab, sub in (("ours", [r for r in rs if r["ours"]]), ("not ours", [r for r in rs if not r["ours"]])):
        if not sub: continue
        po = [r["first_pull_off"] for r in sub]
        frb = [r["frb"]["off"] for r in sub if r.get("frb")]
        p30 = sum(1 for x in po if x is not None and x <= 30) / len(sub)
        pf = [r["first_pull_off"] - r["frb"]["off"] for r in sub if r.get("frb") and r["first_pull_off"] is not None]
        print(f"day {d+1} {lab:8s} n {len(sub):4d} pulled by +30 {p30:5.0%} pull offset p10/50/90 {[pct([x for x in po if x is not None], q) for q in (0.1, 0.5, 0.9)]} "
              f"pull - bot's buy p10/50/90 {[pct(pf, q) for q in (0.1, 0.5, 0.9)]}")
# hourly view of the last 48 h: share of pools pulled by +30, ours vs not
print("\nlast 48 h by 6-hour slice: pulled by +30 (ours n / share | not ours n / share)")
for s in range(20, 28):
    rs = [rows[p] for p in kept[fk] if slice6(rows[p]["launch_ts"]) == s]
    a = [r for r in rs if r["ours"]]; b = [r for r in rs if not r["ours"]]
    f = lambda xs: (len(xs), sum(1 for r in xs if r["first_pull_off"] is not None and r["first_pull_off"] <= 30) / max(1, len(xs)))
    print(f"slice {s}: ours {f(a)[0]:4d} {f(a)[1]:5.0%} | not ours {f(b)[0]:4d} {f(b)[1]:5.0%}")
