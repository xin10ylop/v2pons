# the ce5494bb family's crowd: which wallets buy, and where else (other pools in the census) they buy
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
from common8 import *
P = load_pools(); T = load_txs(); F = load_families()
k = "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true"
pids = F[k]["pids"]
dep = P[pids[0]]["launch_from"]
crowd = collections.Counter()
for t in T.values():
    for pid, kind, rank in t.get("refs", []):
        if pid in pids and kind == "swap" and t["from"] != "0xe71a69f4d55a0bad4e0b0e4b3e4b1a0b6c6c0a61": crowd[t["from"]] += 1
print("crowd wallets in first-8 swaps:", len(crowd), crowd.most_common(40))
# other pools where these wallets appear
other = collections.Counter(); ofam = collections.Counter()
for t in T.values():
    if t["from"] in crowd:
        for pid, kind, rank in t.get("refs", []):
            if pid not in pids: other[pid] += 1; ofam[P[pid]["family"]] += 1
print("other pools with crowd wallets:", len(other)); print(ofam.most_common(20))
# deployer's other launches
dl = [p for p in P.values() if p["launch_from"] == dep]
print("deployer", dep, "launches", len(dl), collections.Counter(p["family"] for p in dl))
# txs from the deployer
print(collections.Counter((t["to"], t["selector"]) for t in T.values() if t["from"] == dep))
# tx shapes of crowd buys
shp = collections.Counter()
for t in T.values():
    if t["from"] in crowd: shp[(t["to"], t["selector"], t["calldata_len"], t["max_prio"], t["type"])] += 1
print(shp.most_common(10))
# nonce ranges of crowd wallets
for w, c in crowd.most_common(12):
    ns = sorted(t["nonce"] for t in T.values() if t["from"] == w)
    print(w, c, ns[:3], ns[-3:])
