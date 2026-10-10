"""Reaction data: every non-operator real-size buy on the operator's launches -> blocks to the next pull, by fee tier.
Roles exactly as research/v4_slowrug_test.py (both data files loaded, as that script was run)."""
import sys, collections, statistics as st, random
sys.path.insert(0, '.')
from load import *
P, S, L, T, TS = load(("/home/user/v2pons/research/data/slowrug.json.gz", "/home/user/v2pons/research/data/slowrug_op.json.gz"))
launcher = {pid: T.get(p["tx"], ["", ""])[1] for pid, p in P.items()}
deployer = {pid: T.get(p["tx"], [""])[0] for pid, p in P.items()}
seen_on = collections.defaultdict(lambda: collections.defaultdict(set)); n_swaps = collections.Counter()
for pid, sw in S.items():
    for x in sw: seen_on[T[x[8]][0]][launcher[pid]].add(pid); n_swaps[T[x[8]][0]] += 1
def roles(pid):
    lz = launcher[pid]; first_nonce = {}; out = []
    for x in sorted(S.get(pid, []), key=lambda x: (x[0], x[1])):
        t = T[x[8]]; w = t[0]; first_nonce.setdefault(w, t[2]); so = seen_on[w]
        if w == deployer[pid]: r = "dep"
        elif first_nonce[w] <= 2: r = "fresh"
        elif len(so[lz]) >= 4 and len(so) == 1 and n_swaps[w] >= 3 * len(so[lz]): r = "wash"
        elif x[3] < 0 and -x[3] < 2e14: r = "dust"
        else: r = "out"
        out.append((x, r, w, t))
    return out
ops = sorted([p for p in P if launcher[p] == OP], key=lambda p: P[p]["bn"])
tiers = {"2-5% (fee >= 1%, to Oct 5)": lambda f: f >= 10000, "< 1% (from Oct 5)": lambda f: f < 10000}
def pull_of(p):
    rems = sorted((x[0], x[1], x[6]) for x in L.get(p, []) if x[5] < 0); return rems[0] if rems else None
rows = []
for p in ops:
    b0 = P[p]["bn"]; pl = pull_of(p); R = roles(p)
    first_out = True
    for x, r, w, t in R:
        if x[3] < 0 and r == "out" and -x[3] >= 2e14:
            if pl is not None and (pl[0], pl[1]) < (x[0], x[1]): continue      # bought after the pull (re-added liquidity): not a candidate
            g = (pl[0] - x[0]) if pl else None
            rows.append({"p": p, "fee": P[p]["fee"], "eth": -x[3] / 1e18, "gap": g, "off": x[0] - b0, "first": first_out, "w": w,
                         "pull_by_dep": pl is not None and T[pl[2]][0] == deployer[p], "to": t[1], "sel": t[4]})
            first_out = False
def bucket(g):
    if g is None: return "no pull (20 min)"
    for hi, name in ((2, "0-2"), (3, "3"), (4, "4"), (5, "5"), (6, "6"), (7, "7"), (8, "8"), (10, "9-10"), (15, "11-15"), (30, "16-30"), (100, "31-100")):
        if g <= hi: return name
    return ">100"
order = ["0-2", "3", "4", "5", "6", "7", "8", "9-10", "11-15", "16-30", "31-100", ">100", "no pull (20 min)"]
for name, sel in tiers.items():
    for label, filt in (("all non-op buys >= 0.0002", lambda r: True), ("first outsider buy per launch", lambda r: r["first"]),
                        ("buys of 0.001-0.002 ETH (our size)", lambda r: 0.001 <= r["eth"] < 0.002), ("buys of 0.0002-0.01 ETH", lambda r: r["eth"] < 0.01)):
        rs = [r for r in rows if sel(r["fee"]) and filt(r)]
        c = collections.Counter(bucket(r["gap"]) for r in rs)
        re = [r["gap"] for r in rs if r["gap"] is not None and r["gap"] <= 30]
        le4 = sum(1 for g in re if g <= 4); ge5 = sum(1 for g in re if g >= 5)
        print(f"{name} | {label}: n {len(rs)} on {len({r['p'] for r in rs})} launches; gap " + ", ".join(f"{k}: {c[k]}" for k in order if c[k]))
        print(f"      pulled within 30 blocks (reaction-like): {len(re)} ({len(re)/max(1,len(rs)):.0%}); of those <= 4 blocks: {le4}, >= 5: {ge5}; "
              f"min {min(re) if re else '-'}, p10/p50/p90 {[sorted(re)[int(q*(len(re)-1))] for q in (.1,.5,.9)] if re else '-'}")
import json; json.dump(rows, open("react_rows.json", "w"))
