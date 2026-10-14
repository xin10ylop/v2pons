"""Every Uniswap v4 Initialize on Ethereum (PoolManager 0x000000000004444c5dc75cb358380d2e3de08a90) from Oct 12 13:00 UTC to the head; cached."""
import sys, json, os; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
PM = "0x000000000004444c5dc75cb358380d2e3de08a90"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
OUT = "c05_eth_inits_cache.jsonl"
done = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
start = max([d["b"] for d in done], default=26176400) + 1
h, _ = rpcx.head("eth_h")
with open(OUT, "a") as f:
    for s in range(start, h + 1, 2000):
        e = min(s + 1999, h)
        for l in rpcx.logs("eth_h", {"address": PM, "topics": [T_INIT]}, s, e):
            d = l["data"][2:]; w = [d[i:i + 64] for i in range(0, len(d), 64)]
            sg = lambda x: x - (1 << 256) if x >= (1 << 255) else x
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "ts": int(l.get("blockTimestamp", "0x0"), 16), "tx": l["transactionHash"], "id": l["topics"][1],
                                "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:], "fee": int(w[0], 16), "ts_": sg(int(w[1], 16)),
                                "hooks": "0x" + w[2][-40:], "sqrtP": int(w[3], 16), "tick": sg(int(w[4], 16))}) + "\n")
        print("scanned", s, e, flush=True)
