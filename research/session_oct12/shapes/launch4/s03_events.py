"""For every launch of the four shapes (s01_launches.json): the launch receipt (which currency is the new coin), every Swap and ModifyLiquidity
of the pool from the launch to +600 blocks (capped at the head), every ModifyLiquidity to the head (late pulls), and the transaction of every
event in the window. Pools are queried in groups (topic1 = a list of pool ids). Caches: cache/s03_rcpt_cache.jsonl, cache/s03_ev_cache.jsonl,
cache/s03_ml_cache.jsonl, cache/s03_tx_cache.jsonl; writes s03_head.json."""
from common import *
import rpc
WIN = 600
X = json.load(open(J("s01_launches.json")))
head = int(rpc.call("eth_blockNumber", []), 16)
json.dump({"head": head}, open(J("s03_head.json"), "w"))
allp = sorted([dict(r, shape=s) for s, v in X.items() for r in v], key=lambda r: r["lb"])
# 1. launch receipts
R = {r["transactionHash"]: r for r in jl(C("s03_rcpt_cache.jsonl"))}
need = sorted({p["tx"] for p in allp} - set(R))
with open(C("s03_rcpt_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for r in rpc.batch("eth_getTransactionReceipt", [[h] for h in need[i:i + 100]], n=20):
            if r: R[r["transactionHash"]] = r; f.write(json.dumps(r) + "\n")
print("receipts", len(R))
# 2. events in groups
done = {l.strip() for l in open(C("s03_groups_done.txt"))} if os.path.exists(C("s03_groups_done.txt")) else set()
groups, cur = [], []
for p in allp:
    if cur and (len(cur) >= 25 or p["lb"] - cur[0]["lb"] > 30000): groups.append(cur); cur = []
    cur.append(p)
if cur: groups.append(cur)
print(len(allp), "pools in", len(groups), "groups")
fe = open(C("s03_ev_cache.jsonl"), "a"); fm = open(C("s03_ml_cache.jsonl"), "a"); fd = open(C("s03_groups_done.txt"), "a")
for g in groups:
    key = g[0]["pid"] + ":" + str(len(g))
    if key in done: continue
    ids = [p["pid"] for p in g]; a = g[0]["lb"]; b = min(head, max(p["lb"] for p in g) + WIN)
    ev = rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, b)
    for l in ev: fe.write(json.dumps(l) + "\n")
    ml = rpc.logs({"address": PM, "topics": [T_ML, ids]}, b + 1, head) if b < head else []
    for l in ml: fm.write(json.dumps(l) + "\n")
    fd.write(key + "\n"); fe.flush(); fm.flush(); fd.flush()
    print(f"group {g[0]['lb']}..{g[-1]['lb']} ({len(g)} pools): {len(ev)} events to +{WIN}, {len(ml)} later ModifyLiquidity", flush=True)
fe.close(); fm.close(); fd.close()
# 3. transactions of the events inside each pool's window
lbp = {p["pid"]: p["lb"] for p in allp}
ev = jl(C("s03_ev_cache.jsonl")) + jl(C("s03_ml_cache.jsonl"))
hs = {l["transactionHash"] for l in ev if l["topics"][0] == T_ML or int(l["blockNumber"], 16) <= lbp[l["topics"][1]] + WIN}
TX = {t["hash"] for t in jl(C("s03_tx_cache.jsonl"))}
need = sorted(hs - TX)
print("event txs", len(hs), "to fetch", len(need))
with open(C("s03_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for t in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20):
            if t: f.write(json.dumps({k: t[k] for k in ("hash", "from", "to", "value", "nonce", "blockNumber", "transactionIndex", "gasPrice")} | {"sel": t["input"][2:10], "n": (len(t["input"]) - 2) // 2}) + "\n")
print(rpc.STATS)
