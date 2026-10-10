import sys, time
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
b = rpc("eth_getBlockByNumber", ["latest", False]); head = int(b["number"], 16)
print("chain now", time.strftime("%H:%M:%S UTC", time.gmtime(int(b["timestamp"], 16))))
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83462500, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
op = [l for l, t in zip(inits, txs) if t and t["input"][:10] == "0x2fcb9108"]
bts = batch([("eth_getBlockByNumber", [l["blockNumber"], False]) for l in op])
print(f"operator launches since 16:43: {len(op)}")
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
for l, bt in zip(op, bts):
    pid = l["topics"][1]; b0 = int(l["blockNumber"], 16); fee = W(l["data"], 0)
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 2000, head)), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    sw = [(int(x["blockNumber"], 16) - b0, s128(W(x["data"], 0)), W(x["data"], 2), W(x["data"], 3)) for x in ls if x["topics"][0] == T_SWAP]
    pulls = [int(x["blockNumber"], 16) - b0 for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) < 0]
    real = [x for x in sw if x[1] <= -2e14]
    burst = sorted({x[0] for x in real[:3]}); eth = sum(-x[1] for x in real[:3]) / 1e18
    tag = "  <== the dry run's" if pid.startswith("0x4d5739") else ""
    print(f"  {time.strftime('%H:%M:%S', time.gmtime(int(bt['timestamp'], 16)))} fee {fee/1e4:.3f}% burst at +{burst} ({eth:.3f} ETH), pull at +{pulls[0] if pulls else '-'}{tag}")
