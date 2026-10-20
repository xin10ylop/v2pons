"""Compare A vs B tx fingerprints (all keys of fp), buy timing after launch, sizes, sell behaviour, via contract."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
d = json.load(open("b_list.json")); fam = d["fam"]
C = {"A": collections.defaultdict(collections.Counter), "B": collections.defaultdict(collections.Counter)}
off = {"A": [], "B": []}; size = {"A": [], "B": []}
ex = {}
for p in pools:
    for x in p["sw"]:
        g = fam.get(x["from"])
        if g not in ("A", "B"): continue
        f = x["fp"] or {}
        side = "buy" if x["a0"] < 0 else "sell"
        for k, v in f.items(): C[g][(side, k)][str(v)] += 1
        C[g][(side, "via")][x["via"][:10]] += 1; C[g][(side, "to")][(x["to"] or "")[:10]] += 1; C[g][(side, "sel")][x["sel"]] += 1
        if side == "buy": off[g].append(x["bn"] - p["b0"]); size[g].append(-x["a0"] / 1e18)
        ex.setdefault((g, side), f)
for g in "AB":
    print("=====", g, "example buy fp", ex.get((g, "buy")), "\n example sell fp", ex.get((g, "sell")))
    for k in sorted(C[g]): print("  ", k, C[g][k].most_common(6))
    print("  buy offset blocks: min", min(off[g]), "median", st.median(off[g]), "  size median", round(st.median(size[g]), 4), "max", round(max(size[g]), 3))
