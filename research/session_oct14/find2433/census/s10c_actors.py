"""Step 10c: shape-blind repeat early buyers. For every launch outside S1/S2/VB 3.0/5.0 (s10) plus the s05 pools, every buy >= 0.002 ETH in
(L, L+30] by an actor (tx.to + selector) other than the launcher. Actors seen in >= 5 distinct pools are listed with their pools' shape keys,
offset p10/50/90, size, wallets, and the families they hit. Prints s10c_actors.out."""
import collections
from common import *
import s07_traits as S
pools = jl_load("s10_early_cache.jsonl") + [p for p in jl_load("s05_events_cache.jsonl")]
def q(xs, f):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None
def pct(xs): return "%s/%s/%s" % (q(xs, .1), q(xs, .5), q(xs, .9)) if xs else "-"
act = collections.defaultdict(list)
seenpool = set()
for p in pools:
    if p["pid"] in seenpool: continue
    seenpool.add(p["pid"])
    r = S.rows[p["pid"]]
    if r["fam"] in ("VB 3.0", "VB 5.0", "VB 2.433"): continue
    got = set()
    for s in S.swaps(p, r):
        if not s["buy"] or s["bn"] <= r["b"] or s["bn"] > r["b"] + 30 or (s["eth"] or 0) < 0.002 or s["h"] == r["h"]: continue
        t = S.TX.get(s["h"])
        if not t or t["f"] == r["frm"]: continue
        a = t["to"][:10] + ":" + t["s"]
        if (a, p["pid"]) in got: continue
        got.add((a, p["pid"]))
        act[a].append(dict(pid=p["pid"], off=s["bn"] - r["b"], eth=s["eth"], f=t["f"], fam=r["fam"] or r["key"], t=r["t"]))
print("pools scanned", len(seenpool), "(launches outside VB 3.0/5.0/2.433, S1, S2; window +30, buys >= 0.002 ETH)")
print("actors with >= 5 pools:")
for a, xs in sorted(act.items(), key=lambda kv: -len(kv[1])):
    if len(xs) < 5: continue
    fams = collections.Counter(x["fam"] for x in xs)
    print("\n %s pools %d  off %s  eth %s  wallets %d  %s..%s" % (a, len(xs), pct([x["off"] for x in xs]), pct([round(x["eth"], 4) for x in xs]), len({x["f"] for x in xs}), hm(min(x["t"] for x in xs)), hm(max(x["t"] for x in xs))))
    for k, v in fams.most_common(5): print("     %4d %s" % (v, k))
