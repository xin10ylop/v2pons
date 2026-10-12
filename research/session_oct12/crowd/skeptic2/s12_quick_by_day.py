"""by launch day: triggered pools, pulled within 20 / 30 / 40 blocks after the engine's trigger (pulls after + 300 from reaction/r04_pools_cache.jsonl)"""
from common import *
import collections
P = {p["pool"]: p for p in jl(J("s04_pools_cache.jsonl"))}
R = {}
for l in open(J("../reaction/r04_pools_cache.jsonl")):
    r = json.loads(l); R[r["pool"]] = r
D = collections.defaultdict(lambda: [0, 0, 0, 0])
for pool, p in P.items():
    if p["trig"] is None: continue
    pull = p["pull"]["off"] if p["pull"] else R[pool]["pull_off"]
    d = time.strftime("%m-%d", time.gmtime(p["ts"])); D[d][0] += 1
    if pull is not None:
        D[d][1] += pull - p["trig"] <= 20; D[d][2] += pull - p["trig"] <= 30; D[d][3] += pull - p["trig"] <= 40
print("by launch day: triggered pools, pulled within 20 / 30 / 40 blocks after the trigger")
for d in sorted(D): print(" ", d, D[d])
