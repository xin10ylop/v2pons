"""Every Swap, ModifyLiquidity and Donate of every 9983bb8c pool (s01 core, 8 days) from its launch to the head, pools queried in groups of 30
(topic1 = a list of pool ids), in chunks of 500k blocks. Then the launch receipts. Caches: cache/s03_ev_cache.jsonl, cache/s03_done.txt,
cache/s03_rcpt_cache.jsonl; writes s03_head.json. Prints s03_events.out."""
from common import *
import rpc, collections
X = json.load(open(J("s01_launches.json"))); core = X["core"]
head = int(rpc.call("eth_blockNumber", []), 16)
json.dump({"head": head, "t": time.time()}, open(J("s03_head.json"), "w"))
done = {}
if os.path.exists(C("s03_done.txt")):
    for l in open(C("s03_done.txt")):
        k, v = l.split(); done[k] = int(v)
pools = sorted(core, key=lambda r: r["lb"])
groups = [pools[i:i + 30] for i in range(0, len(pools), 30)]
fe = open(C("s03_ev_cache.jsonl"), "a"); fd = open(C("s03_done.txt"), "a")
n_ev = 0
for g in groups:
    key = g[0]["pid"][:18] + "_" + str(len(g))
    a0 = max(g[0]["lb"], done.get(key, g[0]["lb"] - 1) + 1)
    ids = [p["pid"] for p in g]
    for a in range(a0, head + 1, 500_000):
        b = min(a + 499_999, head)
        ev = rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML, T_DONATE], ids]}, a, b)
        for l in ev: fe.write(json.dumps(l) + "\n")
        n_ev += len(ev)
        fe.flush(); fd.write(f"{key} {b}\n"); fd.flush()
    print(f"group from {g[0]['lb']} ({len(g)} pools) done to {head}", flush=True)
fe.close(); fd.close()
print("new events", n_ev)
ev = {}
for l in jl(C("s03_ev_cache.jsonl")): ev[(l["transactionHash"], l["logIndex"])] = l
cnt = collections.Counter(l["topics"][0] for l in ev.values())
print("events:", {"Swap": cnt[T_SWAP], "ModifyLiquidity": cnt[T_ML], "Donate": cnt[T_DONATE]}, "pools with events", len({l["topics"][1] for l in ev.values()}))
R = {r["transactionHash"]: r for r in jl(C("s03_rcpt_cache.jsonl"))}
need = sorted({p["tx"] for p in core} - set(R))
with open(C("s03_rcpt_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for r in rpc.batch("eth_getTransactionReceipt", [[h] for h in need[i:i + 100]], n=20):
            if r: R[r["transactionHash"]] = r; f.write(json.dumps(r) + "\n")
print("launch receipts", len(R))
print(rpc.STATS)
