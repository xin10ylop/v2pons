import sys, json, collections; sys.path.insert(0, "..")
from chain import *
A = 83394000; head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, "0x"+"0"*0 if False else None, "0x" + "0"*64]}, A, head)
print("inits", len(inits))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
P = {}
for l, t in zip(inits, txs):
    d = l["data"]
    if d[2+64*2+24:2+64*3] != "0"*40: continue
    if t["input"][:10] != "0x2fcb9108": continue
    P[l["topics"][1]] = {"b0": int(l["blockNumber"], 16), "fee": W(d, 0), "dep": t["from"].lower(), "launcher": t["to"].lower(), "tx": t["hash"]}
print("operator launches", len(P))
pids = sorted(P, key=lambda p: P[p]["b0"]); ev = collections.defaultdict(list)
for i in range(0, len(pids), 40):
    bt = pids[i:i+40]; lo = min(P[p]["b0"] for p in bt); hi = min(max(P[p]["b0"] for p in bt) + 6000, head)
    for a in range(lo, hi + 1, 50000):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 49999, hi)): ev[l["topics"][1]].append(l)
hs = sorted({l["transactionHash"] for p in pids for l in ev[p]})
print("txs", len(hs))
TX = {}
for i in range(0, len(hs), 500):
    r = batch([("eth_getTransactionByHash", [h]) for h in hs[i:i+500]])
    for h, t in zip(hs[i:i+500], r):
        if t: TX[h] = [t["from"].lower(), t["to"].lower() if t["to"] else "", int(t["nonce"], 16), int(t["transactionIndex"], 16), t["input"][:10]]
json.dump({"P": P, "ev": ev, "TX": TX, "head": head}, open("newsch.json", "w"))
