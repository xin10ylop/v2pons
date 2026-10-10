"""Every v2.433 family launch from FROM to (head - 300): Initialize logs on the PoolManager, the launch tx filter (to the PositionManager,
1,444 bytes, 2.4333285 ETH, fee 2500, tick spacing 50, no hooks); per pool: full blocks b0..b0+SCAN, the launch receipt; all the family's
Swap/ModifyLiquidity logs over [first b0, head]; the transactions of every swap/ML outside the block windows. -> data.pkl (incremental)"""
import sys, os, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE)
sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; VAL = 2433328500000000000
FROM = 84856239; SCAN = 36
OUT = os.path.join(HERE, "data.pkl")
D = pickle.load(open(OUT, "rb")) if os.path.exists(OUT) else {"pools": {}, "init_scanned_to": FROM - 1, "txcache": {}}
head = int(rpc("eth_blockNumber", []), 16); D["head"] = head; end = head - 300; D["end"] = end
# 1. launches
a = D["init_scanned_to"] + 1
if a <= end:
    L = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, end)
    hs = sorted({l["transactionHash"] for l in L}); tx = {}
    for i in range(0, len(hs), 50):
        for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
            if t: tx[h] = t
    n_new = 0
    for l in L:
        d = l["data"]; t = tx.get(l["transactionHash"])
        if not t: print("missing tx", l["transactionHash"]); continue
        hooks = d[2 + 64 * 2 + 24: 2 + 64 * 3]
        fam = (t["to"] or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and int(t["value"], 16) == VAL
        shape = W(d, 0) == 2500 and sgn(W(d, 1)) == 50 and hooks == "0" * 40
        if fam and not shape: print("family tx but other shape", l["transactionHash"], W(d, 0), sgn(W(d, 1)), hooks)
        if fam and shape:
            pid = l["topics"][1]
            D["pools"][pid] = {"meta": {"pid": pid, "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "sp0": W(d, 3), "tick0": sgn(W(d, 4)),
                                         "from": t["from"].lower(), "txindex": int(l["transactionIndex"], 16), "input": t["input"]}}
            n_new += 1
    D["init_scanned_to"] = end
    print(f"Initialize (ETH pairs) {len(L)} in [{a},{end}], family {n_new}", flush=True)
    pickle.dump(D, open(OUT, "wb"))
# 2. blocks and receipts
for pid, R in sorted(D["pools"].items(), key=lambda kv: kv[1]["meta"]["b0"]):
    b0 = R["meta"]["b0"]
    if "blocks" not in R or any(b is None for b in R["blocks"]):
        n = min(SCAN, head - b0 + 1)
        R["blocks"] = batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(n)])
        R["rec"] = rpc("eth_getTransactionReceipt", [R["meta"]["tx"]])
        print("blocks", pid[:10], b0, len(R["blocks"]), sum(len(b["transactions"]) for b in R["blocks"] if b), flush=True)
        time.sleep(0.2)
pickle.dump(D, open(OUT, "wb"))
# 3. the family's Swap/ModifyLiquidity logs to the head (all pools in one topic list, chunked)
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["b0"])
lo = D["pools"][pids[0]]["meta"]["b0"]
allogs = []
for i in range(0, len(pids), 40):
    ch = pids[i:i + 40]
    allogs += logs({"address": PM, "topics": [[T_SWAP, T_ML], ch]}, min(D["pools"][p]["meta"]["b0"] for p in ch), head)
D["logs_to"] = head
by = {}
for l in allogs: by.setdefault(l["topics"][1], []).append(l)
for pid in pids: D["pools"][pid]["logs"] = sorted(by.get(pid, []), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
print("logs", len(allogs), flush=True)
# 4. tx of each log outside the block windows (who bought / who pulled)
inwin = set()
for R in D["pools"].values():
    for b in R["blocks"]:
        if b:
            for t in b["transactions"]: D["txcache"].setdefault(t["hash"], {k: t[k] for k in ("hash", "from", "to", "input", "value", "blockNumber", "transactionIndex")})
need = sorted({l["transactionHash"] for l in allogs} - set(D["txcache"]))
for i in range(0, len(need), 50):
    for h, t in zip(need[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in need[i:i + 50]])):
        if t: D["txcache"][h] = {k: t[k] for k in ("hash", "from", "to", "input", "value", "blockNumber", "transactionIndex")}
print("tx fetched", len(need), flush=True)
# 5. base fees of the blocks of those logs (for gas at a landing outside the window, rarely needed)
pickle.dump(D, open(OUT, "wb"))
print("done", len(D["pools"]), "head", head, "end", end)
