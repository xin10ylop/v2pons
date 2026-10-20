import time
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
b = rpc("eth_getBlockByNumber", ["latest", False]); head = int(b["number"], 16); tnow = int(b["timestamp"], 16)
lo = head - int(2 * 3600 / 0.103)
inits = []
for a in range(lo, head + 1, 99999):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, a, min(a + 99998, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
ops = [(l, t) for l, t in zip(inits, txs) if t and t["to"] == ORIG]
pids = [l["topics"][1] for l, _ in ops]; b0 = {l["topics"][1]: int(l["blockNumber"], 16) for l, _ in ops}
sw = logs({"address": PM, "topics": [T_SWAP, pids]}, min(b0.values()), head) if pids else []
ml = logs({"address": PM, "topics": [T_ML, pids]}, min(b0.values()), head) if pids else []
for l, t in ops:
    p = l["topics"][1]; s = b0[p]; d = l["data"]
    buys = sorted(int(x["blockNumber"], 16) - s for x in sw if x["topics"][1] == p and (lambda a0: (a0 - (1 << 256) if a0 >= 1 << 255 else a0))(int(x["data"][2:66], 16)) <= -2e14)
    pulls = sorted(int(x["blockNumber"], 16) - s for x in ml if x["topics"][1] == p and int(x["data"][2 + 128: 2 + 192], 16) >= 1 << 255)
    print(time.strftime("%H:%M:%S", time.gmtime(tnow - (head - s) * 0.103)), f"fee {W(d,0)/1e4:.3f}%", "real buys at", buys[:8], "pull at", pulls[:1])
