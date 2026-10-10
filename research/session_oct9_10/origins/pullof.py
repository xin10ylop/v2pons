"""pull block(s) of the pool created by a launch tx: Initialize log -> pid -> ModifyLiquidity with negative delta. Usage: pullof.py txhash [span]"""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
span = int(sys.argv[2]) if len(sys.argv) > 2 else 120000
for h in sys.argv[1].split(","):
    r = rpc("eth_getTransactionReceipt", [h])
    pid = [l["topics"][1] for l in r["logs"] if l["address"].lower() == PM and l["topics"][0] == T_INIT][0]
    bn = int(r["blockNumber"], 16); out = []
    for a in range(bn, bn + span, 30000):
        for x in logs({"address": PM, "topics": [T_ML, pid]}, a, a + 29999):
            d = sgn(W(x["data"], 2))
            if d < 0: out.append(int(x["blockNumber"], 16))
        if out: break
    print(h, "launch", bn, "pid", pid[:12], "pulls", out, flush=True)
