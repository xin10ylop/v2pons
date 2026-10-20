"""Step 5: the fleet's first buy T (offset from launch L and from the liquidity add A), per hour; the sentinel's offset; the add's offset."""
import collections, datetime, statistics
from common import *
pools = load_pools()
def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))] if xs else None
def best_window(xs, w):
    if not xs: return (None, 0)
    best = max(range(min(xs), max(xs) + 1), key=lambda c: sum(1 for x in xs if abs(x - c) <= w))
    return best, sum(1 for x in xs if abs(x - best) <= w) / len(xs)
H = 3600
t0 = min(p["ts"] for p in pools)
print("pools", len(pools), "with add", sum("add_bn" in p for p in pools), "with T", sum(p["T"] is not None for p in pools))
rows = []
for p in pools:
    sen = [s for s in p["swaps"] if s["k"] == "sentinel"]
    r57 = [s for s in p["swaps"] if s["k"] == "r57"]
    rows.append(dict(h=datetime.datetime.fromtimestamp(p["ts"], datetime.UTC).strftime("%m-%d %H"), L=p["L"], A=p.get("add_off"), T=p["T"],
                     TA=(p["T"] - p["add_off"]) if p["T"] is not None and "add_off" in p else None,
                     sen=(sen[0]["o"] - p["add_off"]) if sen and "add_off" in p else None, r57=(r57[0]["o"] if r57 else None),
                     pull=p.get("pull_off")))
def summ(sel, lab):
    T = [r["T"] for r in sel if r["T"] is not None]; TA = [r["TA"] for r in sel if r["TA"] is not None]
    A = [r["A"] for r in sel if r["A"] is not None]; S = [r["sen"] for r in sel if r["sen"] is not None]
    b1 = best_window(TA, 1); b2 = best_window(TA, 2); c1 = best_window(T, 1); c2 = best_window(T, 2)
    print(f"{lab:10s} n {len(sel):3d} T {len(T):3d}  T-L p10/50/90 {pct(T,.1)}/{pct(T,.5)}/{pct(T,.9)} best+-1 {c1[0]}:{c1[1]:.0%} +-2 {c2[0]}:{c2[1]:.0%}"
          f" | T-A p10/50/90 {pct(TA,.1)}/{pct(TA,.5)}/{pct(TA,.9)} best+-1 {b1[0]}:{b1[1]:.0%} +-2 {b2[0]}:{b2[1]:.0%} | A-L {pct(A,.1)}/{pct(A,.5)}/{pct(A,.9)}"
          f" | sentinel-A {collections.Counter(S).most_common(3)}")
summ(rows, "all 24h")
for h in sorted({r["h"] for r in rows}): summ([r for r in rows if r["h"] == h], h)
print("no fleet buy:", [(r["L"], r["pull"]) for r in rows if r["T"] is None])
print("T-A sorted:", sorted(r["TA"] for r in rows if r["TA"] is not None))
jdump(rows, "s05_timing.json")
