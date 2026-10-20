"""own fetch: every log of each line pool in [launch, launch + WIN] (one eth_getLogs per pool, 10 per POST), stored compact:
Swap -> ["s", bn, ti, li, sender, recipient, amount0, amount1, sqrtP, liquidity, tick, tx]; Burn -> ["b", bn, ti, li, owner, tl, tu, amount, a0, a1, tx];
Mint -> ["m", bn, ti, li, tx]; anything else -> ["o", bn, topic0]. -> s02_logs_cache.jsonl (resumable)."""
from common import *
import rpc
WIN = int(sys.argv[1]) if len(sys.argv) > 1 else 300
L = json.load(open(J("s01_launches.json"))); head = json.load(open(J("s01_meta.json")))["head"]
done = {x["pool"] for x in jl(J("s02_logs_cache.jsonl"))}
todo = [x for x in L if x["pool"] not in done]
print(f"{len(L)} launches, {len(todo)} to fetch, window +{WIN}", flush=True)
def comp(l):
    t = l["topics"]; d = l["data"]; bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16); h = l["transactionHash"]
    if t[0] == T_SW: return ["s", bn, ti, li, "0x" + t[1][-40:], "0x" + t[2][-40:], si("0x" + word(d, 0)), si("0x" + word(d, 1)), int(word(d, 2), 16), int(word(d, 3), 16), si("0x" + word(d, 4)), h]
    if t[0] == T_BU: return ["b", bn, ti, li, "0x" + t[1][-40:], si(t[2]), si(t[3]), int(word(d, 0), 16), int(word(d, 1), 16), int(word(d, 2), 16), h]
    if t[0] == T_MI: return ["m", bn, ti, li, h]
    return ["o", bn, t[0][:10]]
f = open(J("s02_logs_cache.jsonl"), "a")
for i in range(0, len(todo), 10):
    ch = todo[i:i + 10]
    res = rpc.batch("eth_getLogs", [[{"address": x["pool"], "fromBlock": hex(x["lb"]), "toBlock": hex(min(head, x["lb"] + WIN))}] for x in ch], n=10)
    for x, la in zip(ch, res):
        if la is None: print("missing", x["pool"]); continue
        ev = sorted((comp(l) for l in la), key=lambda c: (c[1], c[2] if c[0] != "o" else 0, c[3] if c[0] != "o" else 0))
        f.write(json.dumps({"pool": x["pool"], "to": min(head, x["lb"] + WIN), "ev": ev}) + "\n")
    f.flush()
    if i % 200 == 0: print(i, rpc.STATS, flush=True)
f.close(); print("done", rpc.STATS)
