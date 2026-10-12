"""Every Swap and ModifyLiquidity log of the C-1 pools (c01) from the start block to the head (topic-OR on pool ids, 100k-block chunks),
plus every Swap whose sender is our relay over the same range (any pool). Writes c02_events.jsonl, c02_relay_swaps.json, c02_head.json."""
from common import *
import rpc
X = json.load(open(J("c01_launches.json"))); M = json.load(open(J("c01_meta.json")))
head = int(rpc.call("eth_blockNumber", []), 16)
ids = sorted(set(x["pid"] for x in X)); a0 = min(x["lb"] for x in X)
out = []
for g in range(0, len(ids), 100):
    grp = ids[g:g + 100]
    for a in range(a0, head + 1, 100000):
        b = min(a + 99999, head)
        out += rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], grp]}, a, b)
seen = set(); ev = []
for l in out:
    k = (l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); ev.append(l)
ev.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
with open(J("c02_events.jsonl"), "w") as f:
    for l in ev: f.write(json.dumps({k: l[k] for k in ("blockNumber", "logIndex", "transactionIndex", "transactionHash", "topics", "data")}) + "\n")
rel = []
for a in range(M["start"], head + 1, 100000):
    rel += rpc.logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY[2:]]}, a, min(a + 99999, head))
json.dump(rel, open(J("c02_relay_swaps.json"), "w")); json.dump({"head": head}, open(J("c02_head.json"), "w"))
print(f"head {head}; events {len(ev)} (swaps {sum(l['topics'][0] == T_SWAP for l in ev)}, modifyLiquidity {sum(l['topics'][0] == T_ML for l in ev)}); relay swaps (all pools) {len(rel)}; in C-1 pools {sum(l['topics'][1] in set(ids) for l in rel)}")
print("rpc", rpc.STATS)
