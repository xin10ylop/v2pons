"""Stage 6b: (1) user transactions per block at each d before T (is the window just before T simply fuller?); (2) do the keys with the
largest d1-4 excess on the discovery pools keep it on the held-out pools (and the reverse)?"""
import pickle, collections, statistics as st
from lib import *
E = pickle.load(open("events.pkl", "rb")); rows = E["rows"]; facts = {f["pid"]: f for f in E["facts"]}
pids = sorted([f["pid"] for f in E["facts"] if f["near_ok"]], key=lambda k: facts[k]["L"])
n = len(pids); disc = set(pids[: (2 * n) // 3]); hold = set(pids[(2 * n) // 3:])
kb = KV("blk"); SYS = "0x00000000000000000000000000000000000a4b05"
print("user txs per block at d blocks before T (T's block counted whole), all pools:")
for d in range(0, 13):
    v = [sum(1 for t in kb.d[str(facts[k]["Tbn"] - d)]["txs"] if (t["from"] or "").lower() != SYS) for k in pids]
    print(f"  d {d:2d}: mean {st.mean(v):.2f}")
exec(open("s6_precursors.py").read().split("occ = collections")[0].split("def keys")[1].join(["def keys", ""]) if False else "")
import importlib.util
src = open("s6_precursors.py").read(); keys_src = src[src.index("def keys(r):"): src.index("occ = collections")]
exec(keys_src)
occ = collections.defaultdict(lambda: collections.defaultdict(set))
for r in rows:
    if r["pos"] == "before" and r["pid"] in disc | hold and 1 <= r["d"] <= 12:
        for k in keys(r): occ[k][r["d"]].add(r["pid"])
def exc(k, S):
    w = lambda a, b: len(set().union(*[occ[k][d] & S for d in range(a, b + 1)]))
    return (w(1, 4) - (w(5, 8) + w(9, 12)) / 2) / len(S)
for A, B, la, lb in ((disc, hold, "discovery", "held out"), (hold, disc, "held out", "discovery")):
    top = sorted(occ, key=lambda k: -exc(k, A))[:12]
    print(f"\ntop d1-4 excess keys on the {la} pools, and the same keys on the {lb} pools (share of pools):")
    for k in top: print(f"  {k[:60]:60s} {la} {100*exc(k, A):+5.1f}%   {lb} {100*exc(k, B):+5.1f}%")
