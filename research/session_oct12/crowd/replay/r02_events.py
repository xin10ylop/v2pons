"""Pool events of the r01 launches: (a) every Swap/Mint/Burn in [launch, launch + WIN] (chunks of 20k blocks, address lists of the pools whose
window overlaps the chunk); (b) every Burn of every pool from its launch to the head (the first pull may come thousands of blocks later).
Writes r02_events_cache.jsonl (compact raw logs) and r02_meta.json (head, WIN)."""
from common import *
import rpc
WIN = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
X = json.load(open(J("r01_launches.json")))
head = int(rpc.call("eth_blockNumber", []), 16)
lb = {x["pool"]: x["lb"] for x in X}
a0 = min(lb.values()); out = []; CH = 20000
for a in range(a0, head + 1, CH):
    b = min(a + CH - 1, head)
    ps = sorted(p for p, l in lb.items() if l <= b and l + WIN >= a)
    for i in range(0, len(ps), 40):
        out += rpc.logs({"address": ps[i:i + 40], "topics": [[T_SW, T_MI, T_BU]]}, a, b)
print(f"window events {len(out)}; rpc {rpc.STATS}", flush=True)
burns = []; ps = sorted(lb)
for i in range(0, len(ps), 50):
    grp = ps[i:i + 50]; g0 = min(lb[p] for p in grp)
    for a in range(g0, head + 1, 400000):
        burns += rpc.logs({"address": grp, "topics": [T_BU]}, a, min(a + 399999, head))
print(f"burns to head {len(burns)}; rpc {rpc.STATS}", flush=True)
seen = set(); ev = []
for l in out + burns:
    k = (l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); ev.append(l)
ev.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
with open(J("r02_events_cache.jsonl"), "w") as f:
    for l in ev:
        f.write(json.dumps({"a": l["address"].lower(), "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                            "tx": l["transactionHash"], "t": l["topics"], "d": l["data"]}) + "\n")
json.dump({"head": head, "win": WIN}, open(J("r02_meta.json"), "w"))
import collections
c = collections.Counter({T_SW: "swap", T_MI: "mint", T_BU: "burn"}[l["topics"][0]] for l in ev)
print(f"head {head}; events {len(ev)} {dict(c)}; rpc {rpc.STATS}")
