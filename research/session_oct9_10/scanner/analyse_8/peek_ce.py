import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
from common8 import *
P = load_pools(); T = load_txs(); F = load_families()
T.update(json.load(open("cache/ce_txs.json")))
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
crowd = set(json.load(open("crowd_ce.json")))
k = "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true"
pids = F[k]["pids"]; E = load_events(set(pids))
allfrom = collections.Counter(); first_seen = {}
for pid in pids:
    for x in E[pid]["swaps"]:
        t = T[x["tx"]]; allfrom[t["from"]] += 1
print(len(allfrom)); print(allfrom.most_common(60))
for pid in pids:
    p = P[pid]; e = E[pid]; L0 = p["launch_block"]
    print("=====", pid[:10], "pull", p["first_pull_rel"], "nswaps", len(e["swaps"]))
    for x in e["swaps"]:
        t = T[x["tx"]]
        tag = "DUST" if t["from"] == DUST else ("crowd" if t["from"] in crowd else "OTHER")
        if tag != "crowd" or (p["first_pull_rel"] and x["bn"] - L0 > p["first_pull_rel"] - 60):
            print("  %5d %+.6f %s %s %s %s %d prio %s nonce %s" % (x["bn"] - L0, -x["a0"] / 1e18, tag, t["from"][:10], (t["to"] or "")[:10], t["selector"], t["calldata_len"], t.get("max_prio"), t["nonce"]))
