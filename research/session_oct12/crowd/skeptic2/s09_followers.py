"""the bait-and-pull since Oct 10: are the quick post-trigger pulls the pools where follower bots buy right after the crowd's first real buy?
Followers: outside wallets buying within 5 blocks after the trigger in >= 10 pools. Per period: triggered pools with / without a follower buy in
[trigger, trigger + 5], pull within 20 / 30 / 40 of the trigger. Fisher for the regime change (Oct 10-12 vs Oct 3-9)."""
from common import *
import collections
P = {p["pool"]: p for p in json.load(open(J("s04_pools.json")))}
R = {}
for l in open(J("../reaction/r04_pools_cache.jsonl")):
    r = json.loads(l); R[r["pool"]] = r
OCT10 = 1791590400
cnt = collections.Counter(); first = {}
for pool, p in P.items():
    if p["trig"] is None: continue
    ws = {s["from"] for s in R[pool]["sw"] if s["k"] == "other" and s["from"] and s["dq"] > 0 and p["trig"] <= s["off"] <= p["trig"] + 5}
    for w in ws:
        cnt[w] += 1; first[w] = min(first.get(w, 1e18), p["ts"])
F = {w for w, n in cnt.items() if n >= 10}
print("follower wallets (>= 10 pools, buying within 5 blocks after the trigger):", [(w[:10], cnt[w], utc(first[w])) for w in sorted(F, key=lambda w: -cnt[w])])
rows = []
for pool, p in P.items():
    if p["trig"] is None: continue
    pull = p["pull"]["off"] if p["pull"] else R[pool]["pull_off"]
    fol = any(s["k"] == "other" and s["from"] in F and s["dq"] > 0 and p["trig"] <= s["off"] <= p["trig"] + 5 for s in R[pool]["sw"])
    rows.append({"ts": p["ts"], "trig": p["trig"], "d": (pull - p["trig"]) if pull is not None else None, "fol": fol})
for lab, f in (("Oct 3-9", lambda r: r["ts"] < OCT10), ("Oct 10-12", lambda r: r["ts"] >= OCT10)):
    for fl in (True, False):
        g = [r for r in rows if f(r) and r["fol"] == fl]
        k = lambda x: sum(1 for r in g if r["d"] is not None and r["d"] <= x)
        print(f"  {lab:<10} follower buy after the trigger {'yes' if fl else 'no ':<3}: n {len(g):>4}; pulled within 20 {k(20)}, 30 {k(30)}, 40 {k(40)}; triggers <= +60: {sum(1 for r in g if r['trig'] <= 60)}")
a = sum(1 for r in rows if r["ts"] >= OCT10 and r["d"] is not None and r["d"] <= 30); n1 = sum(1 for r in rows if r["ts"] >= OCT10)
c = sum(1 for r in rows if r["ts"] < OCT10 and r["d"] is not None and r["d"] <= 30); n2 = sum(1 for r in rows if r["ts"] < OCT10)
print(f"pulled within 30 of the trigger: Oct 10-12 {a}/{n1} vs Oct 3-9 {c}/{n2}: one-sided Fisher p {fisher1(a, n1 - a, c, n2 - c):.2g}")
a = sum(1 for r in rows if r["ts"] >= OCT10 and r["d"] is not None and r["d"] <= 20); c = sum(1 for r in rows if r["ts"] < OCT10 and r["d"] is not None and r["d"] <= 20)
print(f"pulled within 20 of the trigger: Oct 10-12 {a}/{n1} vs Oct 3-9 {c}/{n2}: one-sided Fisher p {fisher1(a, n1 - a, c, n2 - c):.2g}; Oct 10-12 rate {100*a/n1:.2f}% (Wilson {100*wilson(a,n1)[0]:.2f}-{100*wilson(a,n1)[1]:.2f}%)")
