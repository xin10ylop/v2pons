"""out-of-sample check of the copy-trade idea: rank every wallet that bought >= 150 window curves in the train days (Oct 4-7) by the copy replay
(k=2, cap=300, stake 0.0058) on those days; test the top 5 (and the pooled top 5) on Oct 8-11 at k=1/2, cap 100/300/1000."""
import pickle, json, collections
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
split = 83020000   # ~2026-10-08 00:00 UTC
print("split block day", day(split))
cur = [c for c in TR if 79984897 <= CE[c]["bn"] <= head - 3100]
first = collections.defaultdict(dict)   # wallet -> curve -> (first buy bn, first sell after)
for c in cur:
    ev = TR[c]
    for r in ev:
        if r[3] == "B" and r[4][0] == r[4][1]:
            w = r[4][1]
            if c not in first[w] and r[2] != CE[c]["tx"]: first[w][c] = r[0]
def copy(w, curves, k, cap, stake=0.0058):
    R = []
    for c in curves:
        b0 = first[w][c]; ev = TR[c]
        ms = [r for r in ev if r[3] == "S" and w in r[4] and r[0] > b0]
        xb = min(ms[0][0] + k, b0 + k + cap) if ms else b0 + k + cap
        cf = cfee(ev); cf = 0.02 if cf is None else cf
        x = replay(ev, b0 + k, xb, stake, 0.0, cf)
        if x is None or x["grad"]: continue
        R.append(x["ret"])
    return R
cand = []
for w, d in first.items():
    tr = [c for c in d if CE[c]["bn"] < split]
    if len(tr) < 150: continue
    R = copy(w, tr, 2, 300)
    if R: cand.append((sum(R) / len(R), len(R), w))
cand.sort(reverse=True)
print("candidates", len(cand)); out = {"train_top10": [(round(m, 4), n, w) for m, n, w in cand[:10]], "test": {}}
for m, n, w in cand[:10]: print("train", round(m, 4), n, w)
top = [w for _, _, w in cand[:5]]
span_test = (bts(head - 3100) - bts(split)) / 86400
for k in (1, 2):
    for cap in (100, 300, 1000):
        pooled = []
        for w in top:
            te = [c for c in first[w] if CE[c]["bn"] >= split]
            R = copy(w, te, k, cap); pooled += R
            out["test"][f"{w} k={k} cap={cap}"] = stats(R, 0.0058, span_test)
        s = stats(pooled, 0.0058, span_test); out["test"][f"pooled top5 k={k} cap={cap}"] = s
        print("TEST pooled top5", f"k={k} cap={cap}", {z: s.get(z) for z in ("n", "mean", "median", "win", "worst", "best", "usd_per_day")})
        for w in top: print("     ", w[:10], {z: out["test"][f"{w} k={k} cap={cap}"].get(z) for z in ("n", "mean", "median", "win")})
json.dump(out, open(os.path.join(OUT, "k33_copy_oos.json"), "w"), indent=1)
# by day for the pooled test (k=1/2, cap 300) at both stakes
byd = {}
for k in (1, 2):
    for stake in (0.002, 0.0058):
        d = collections.defaultdict(list)
        for w in top:
            te = [c for c in first[w] if CE[c]["bn"] >= split]
            for c in te:
                R = copy(w, [c], k, 300, stake)
                if R: d[day(CE[c]["bn"])].append(R[0])
        allr = [x for v in d.values() for x in v]
        byd[f"k={k} stake={stake}"] = {"all": stats(allr, stake, span_test), "by_day": {dd: [len(v), round(sum(v) / len(v), 4), round(sorted(v)[len(v) // 2], 4), round(sum(v) * stake * USD, 2)] for dd, v in sorted(d.items())}}
        print("pooled test by day", k, stake, byd[f"k={k} stake={stake}"])
out["test_by_day_cap300"] = byd
json.dump(out, open(os.path.join(OUT, "k33_copy_oos.json"), "w"), indent=1)
