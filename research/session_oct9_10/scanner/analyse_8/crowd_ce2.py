import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
from common8 import *
P = load_pools(); T = load_txs(); F = load_families()
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
k = "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true"
pids = set(F[k]["pids"])
crowd = set()
for t in T.values():
    for pid, kind, rank in t.get("refs", []):
        if pid in pids and kind == "swap" and t["from"] != DUST: crowd.add(t["from"])
other = collections.defaultdict(list)
for t in T.values():
    if t["from"] in crowd:
        for pid, kind, rank in t.get("refs", []):
            if pid not in pids: other[pid].append((t["from"][:10], kind, rank, t["calldata_len"]))
print("crowd", len(crowd), "other pools", len(other))
for pid, v in sorted(other.items(), key=lambda kv: P[kv[0]]["launch_block"]):
    p = P[pid]
    print(pid[:10], p["launch_block"], p["family"][:70], p["launch_from"][:10], p["known"], "n_buys", p["n_buys"], "pull", p["first_pull_rel"], v[:4])
json.dump(sorted(crowd), open("crowd_ce.json", "w"))
