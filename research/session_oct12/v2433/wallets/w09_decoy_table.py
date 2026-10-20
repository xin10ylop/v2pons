"""Decoy-router swaps per hour and per pool family (from w01/w02/w08)."""
from common import *
import collections, bisect
sw = jl(J("w08_dswaps_cache.jsonl"))
ini = {r["pid"]: r for r in jl(J("w01_inits_cache.jsonl"))}
ltx = {t["h"]: t for t in jl(J("w02_ltx_cache.jsonl"))}
bts = sorted((d["b"], d["ts"]) for d in jl(J("w02_bts_cache.jsonl"))); bb = [b for b, _ in bts]
def T(b):
    i = min(bisect.bisect_left(bb, b), len(bb) - 1); b0, t0 = bts[i]; return t0 + (b - b0) / 9.79
def fam(pid):
    i = ini.get(pid)
    if not i: return "pool before Oct 11 12:00"
    t = ltx.get(i["tx"])
    if not t: return f"non-ETH {i['fee']}/{i['ts']}"
    v = int(t["v"]) / 1e18
    return {2.4333285: "v2.433", 3.0: "v3.0", 5.0: "v5.0"}.get(round(v, 7), f"{round(v, 7)} ETH {i['fee']}/{i['ts']} {t['to'][:8]}:{t['len']}")
print(len(sw), "decoy-router swaps")
for r in (DECOY_R, FRONT_R2):
    s = [x for x in sw if x["r"] == r]
    print(f"\n== {r}: {len(s)} swaps; buys {sum(1 for x in s if x['a0'] < 0)}; first {utc(T(s[0]['b'])) if s else '-'}, last {utc(T(s[-1]['b'])) if s else '-'}")
    c = collections.defaultdict(collections.Counter)
    for x in s: c[time.strftime("%m-%d %H", time.gmtime(T(x["b"])))][(fam(x["pid"]), "buy" if x["a0"] < 0 else "sell")] += 1
    for hh in sorted(c): print(" ", hh, sum(c[hh].values()), dict(c[hh].most_common(5)))
print("\nper hour, buys in the volume bot's lines (v2.433 / v3.0 / v5.0) by router")
for r in (DECOY_R, FRONT_R2):
    c = collections.defaultdict(collections.Counter)
    for x in sw:
        if x["r"] != r or x["a0"] >= 0: continue
        f = fam(x["pid"])
        if f in ("v2.433", "v3.0", "v5.0"): c[time.strftime("%m-%d %H", time.gmtime(T(x["b"])))][f] += 1
    print(r[:10], " ".join(f"{hh[6:]}h:{dict(c[hh])}" for hh in sorted(c)))
