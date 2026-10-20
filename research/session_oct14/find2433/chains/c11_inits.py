"""Every Uniswap v4 Initialize on one chain from Oct 12 13:00 UTC to the head, compact rows cached as c11_<chain>_inits_cache.jsonl.
usage: c11_inits.py <chain> <endpoint key> <span>"""
import sys, json, os, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
ch, ep, span = sys.argv[1], sys.argv[2], int(sys.argv[3])
PM = {"base": "0x498581ff718922c3f8e6a244956af099b2652b2b", "uni": "0x1f98400000000000000000000000000000000004", "arb": "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
      "bsc": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df", "eth": "0x000000000004444c5dc75cb358380d2e3de08a90"}[ch]
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
OUT = f"c11_{ch}_inits_cache.jsonl"; META = f"c11_{ch}_meta.json"
meta = json.load(open(META)) if os.path.exists(META) else {}
if "start" not in meta:
    meta["start"] = rpcx.block_at(ep, 1791810000)  # Oct 12 13:00 UTC
    meta["done"] = meta["start"] - 1
h, th = rpcx.head(ep)
sg = lambda x: x - (1 << 256) if x >= (1 << 255) else x
with open(OUT, "a") as f:
    s = meta["done"] + 1
    while s <= h:
        e = min(s + span - 1, h)
        for l in rpcx.logs(ep, {"address": PM, "topics": [T_INIT]}, s, e):
            d = l["data"][2:]; w = [d[i:i + 64] for i in range(0, len(d), 64)]
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "id": l["topics"][1], "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:],
                                "fee": int(w[0], 16), "ts_": sg(int(w[1], 16)), "hooks": "0x" + w[2][-40:], "sqrtP": int(w[3], 16), "tick": sg(int(w[4], 16))}) + "\n")
        f.flush(); meta["done"] = e; meta["head_ts"] = th; json.dump(meta, open(META, "w"))
        print("scanned", s, e, flush=True); s = e + 1
print("DONE", ch, meta, rpcx.STATS)
