"""skeptic fetch: launches of the v2.433 family from the dry-run start to head; Swap+ModifyLiquidity logs of their pools; blocks around them."""
import sys, os, pickle, json, datetime
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn, block_at
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_s.pkl")
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
VAL = 2433328500000000000
t0 = int(datetime.datetime(2026, 10, 10, 8, 24, 24, tzinfo=datetime.timezone.utc).timestamp())
start = block_at(t0)
head = int(rpc("eth_blockNumber", []), 16)
print("start", start, "head", head)
inits = logs({"address": PM, "topics": [T_INIT]}, start, head)
print("Initialize logs", len(inits))
txh = sorted({l["transactionHash"] for l in inits})
txs = dict(zip(txh, batch([("eth_getTransactionByHash", [h]) for h in txh])))
launches = []
for l in inits:
    t = txs[l["transactionHash"]]
    d = l["data"]
    fee = W(d, 0); ts = sgn(W(d, 1)); hooks = l["topics"][3]  # topics: pid, c0, c1 ; data: fee, tickSpacing, hooks, sqrtP, tick
    hooks = W(d, 2)
    ok = (t["to"] or "").lower() == POSM and int(t["value"], 16) == VAL and (len(t["input"]) - 2) // 2 == 1444
    launches.append({"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "txi": int(l["transactionIndex"], 16),
                     "fee": fee, "ts": ts, "hooks": hooks, "sp0": W(d, 3), "tick0": sgn(W(d, 4)), "c0": l["topics"][2], "c1": l["topics"][3],
                     "to": t["to"], "value": int(t["value"], 16), "len": (len(t["input"]) - 2) // 2, "from": t["from"], "fam": ok and fee == 2500 and ts == 50 and hooks == 0})
fam = [x for x in launches if x["fam"]]
print("family launches", len(fam), "other inits", len(launches) - len(fam))
pids = [x["pid"] for x in fam]
lg = []
for i in range(0, len(pids), 20):
    lg += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids[i:i+20]]}, start, head)
print("pool logs", len(lg))
# blocks b0 .. b0+16 for every family launch (full txs), plus receipt of launch
need = sorted({b for x in fam for b in range(x["bn"], x["bn"] + 17)})
blocks = {}
res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in need])
for b, r in zip(need, res): blocks[b] = r
recs = dict(zip([x["tx"] for x in fam], batch([("eth_getTransactionReceipt", [x["tx"]]) for x in fam])))
pickle.dump({"start": start, "head": head, "launches": launches, "fam": fam, "logs": lg, "blocks": blocks, "recs": recs}, open(OUT, "wb"))
print("saved", OUT)
