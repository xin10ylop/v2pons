import sys; sys.path.insert(0, "..")
from chain import *
relay = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
L = logs({"address": PM, "topics": [T_SWAP, None, "0x"+"0"*24+relay[2:]]}, 83341000, 83345000)
hs = [l["transactionHash"] for l in L]
R = batch([("eth_getTransactionReceipt", [h]) for h in hs])
Tx = batch([("eth_getTransactionByHash", [h]) for h in hs])
Bk = batch([("eth_getBlockByNumber", [r["blockNumber"], False]) for r in R])
tot = 0
for l, r, t, b in zip(L, R, Tx, Bk):
    g = int(r["gasUsed"], 16); ep = int(r["effectiveGasPrice"], 16); c = g * ep; tot += c
    gl1 = int(r.get("gasUsedForL1", "0x0"), 16)
    print(int(r["blockNumber"],16), "gasUsed", g, "L1part", gl1, "effGP gwei", ep/1e9, "base", int(b["baseFeePerGas"],16)/1e9, "cost ETH %.3e" % c, "= %.3f%% of stake" % (100*c/1.2e15))
print("mean round trip cost %.3f%% of 0.0012 ETH" % (100*tot/7/1.2e15))
