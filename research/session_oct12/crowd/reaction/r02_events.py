"""every log of each line pool in [launch, launch + WIN] (Swap, Mint, Burn, Collect, ...) -> r02_events_cache.jsonl (one line per pool,
resumable); then, for pools with no Burn in that window, the pool's Burn logs from the launch to the head (single address and topic: any
range is allowed; one call at a time) -> r02_burns_cache.jsonl."""
from common import *
import rpc
WIN = 3000
L = json.load(open(J("r01_launches.json"))); M = json.load(open(J("r01_meta.json"))); head = M["head"]
done = {x["pool"] for x in jl(J("r02_events_cache.jsonl"))}
todo = [x for x in L if x["pool"] not in done]
print(f"{len(L)} launches, {len(todo)} to fetch; head {head}")
f = open(J("r02_events_cache.jsonl"), "a"); n = 0
for i in range(0, len(todo), 10):
    ch = todo[i:i + 10]
    a = rpc.batch("eth_getLogs", [[{"address": x["pool"], "fromBlock": hex(x["lb"]), "toBlock": hex(min(head, x["lb"] + WIN))}] for x in ch], n=10)
    for x, la in zip(ch, a):
        if la is None: print("missing", x["pool"]); continue
        f.write(json.dumps({"pool": x["pool"], "to": min(head, x["lb"] + WIN), "logs": la}) + "\n"); n += 1
    f.flush()
    if i % 200 == 0: print(i, rpc.STATS, flush=True)
f.close(); print("window logs written", n, rpc.STATS)
E = {x["pool"]: x for x in jl(J("r02_events_cache.jsonl"))}
bd = {x["pool"] for x in jl(J("r02_burns_cache.jsonl"))}
need = [x for x in L if x["pool"] in E and not any(l["topics"][0] == T_BU for l in E[x["pool"]]["logs"]) and x["pool"] not in bd]
print(f"pools with no Burn by +{WIN}: {len(need)}")
f = open(J("r02_burns_cache.jsonl"), "a")
for k, x in enumerate(need):
    r = rpc.call("eth_getLogs", [{"address": x["pool"], "topics": [T_BU], "fromBlock": hex(x["lb"]), "toBlock": hex(head)}])
    f.write(json.dumps({"pool": x["pool"], "head": head, "burns": r}) + "\n"); f.flush()
    if k % 100 == 0: print("burns", k, rpc.STATS, flush=True)
print("done", rpc.STATS)
