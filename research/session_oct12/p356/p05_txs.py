"""p05: the transactions behind every swap from the launch to launch + 600 and every Burn/Collect (pull) in the 3,000 blocks, for the 102
launch pools (eth_getTransactionByHash, 20 per POST). -> p05_txs.jsonl (from, to, input, value, nonce, priority fee, gas price, block)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rpc, common as K
X = K.launches(); E = K.events()
want = set()
for x in X:
    o = E[x["pool"]]
    for e in o["ev"]:
        if (e[0] == "s" and e[1] - x["block"] <= 600) or e[0] == "b": want.add(e[-1])
    for e in o["collects"]: want.add(e[-1])
have = set()
if os.path.exists(K.J("p05_txs.jsonl")):
    have = set(json.loads(l)["hash"] for l in open(K.J("p05_txs.jsonl")))
need = sorted(want - have)
print("want", len(want), "need", len(need), flush=True)
for i in range(0, len(need), 100):
    res = rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20)
    with open(K.J("p05_txs.jsonl"), "a") as f:
        for t in res:
            if t is None: continue
            f.write(json.dumps({k: t.get(k) for k in ("hash", "from", "to", "input", "value", "nonce", "blockNumber", "maxPriorityFeePerGas", "maxFeePerGas", "gasPrice", "type", "transactionIndex")}) + "\n")
    print("txs", i + len(res), flush=True)
print("rpc", rpc.STATS)
