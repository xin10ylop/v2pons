"""Ethereum: the single 2.433-shape pool (block 26176810): every Swap and ModifyLiquidity until the pull, with the senders' transactions."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
PM = "0x000000000004444c5dc75cb358380d2e3de08a90"
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
I = [json.loads(l) for l in open("c05_eth_inits_cache.jsonl")]
P = [r for r in I if r["sqrtP"] == 1604517591721945638372359205383840][0]
pid = P["id"]; b0 = P["b"]
sg = lambda x: x - (1 << 256) if x >= (1 << 255) else x
ev = rpcx.logs("eth_h", {"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, b0 + 200)
launch = rpcx.call("eth_h", "eth_getTransactionByHash", [P["tx"]]); lr = rpcx.call("eth_h", "eth_getTransactionReceipt", [P["tx"]])
print("launch", P["tx"], "from", launch["from"], "nonce", int(launch["nonce"], 16), "value", int(launch["value"], 16) / 1e18, "len", (len(launch["input"]) - 2) // 2,
      "gasLimit", int(launch["gas"], 16), "gasUsed", int(lr["gasUsed"], 16), "gp gwei", int(lr["effectiveGasPrice"], 16) / 1e9, "fee/ts", P["fee"], P["ts_"], "c1", P["c1"])
rows = []
for l in ev:
    d = l["data"][2:]; w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
    t = rpcx.call("eth_h", "eth_getTransactionByHash", [l["transactionHash"]])
    b = int(l["blockNumber"], 16)
    if l["topics"][0] == T_SWAP:
        a0, a1 = sg(w[0]), sg(w[1])
        rows.append({"k": "swap", "b": b, "off": b - b0, "ti": int(l["transactionIndex"], 16), "from": t["from"], "to": t["to"], "sel": t["input"][:10], "eth": -a0 / 1e18, "tok": a1 / 1e18,
                     "nonce": int(t["nonce"], 16), "tx": l["transactionHash"], "gp": int(t.get("gasPrice", "0x0"), 16) / 1e9, "sqrtP": w[2]})
    else:
        rows.append({"k": "liq", "b": b, "off": b - b0, "from": t["from"], "to": t["to"], "sel": t["input"][:10], "L": sg(w[2]), "tx": l["transactionHash"]})
for r in rows: print(r)
json.dump({"launch": P, "rows": rows}, open("c09_eth_pool.json", "w"), indent=1)
