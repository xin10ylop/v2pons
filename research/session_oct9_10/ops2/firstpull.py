"""What happened to the LP of the very first launch (by the launcher's own deployer 0x3b11cafa)? ModifyLiquidity events of its pool via eth_getLogs."""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import logs, batch, T_ML, T_SWAP, sgn
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; PID = "0xc62f041f8554e1dbacf01df2ddd3402b28820d73ee762f91c354f5444af2e7dc"
a = 19367696; b = a + 3_000_000
ml = logs({"address": PM, "topics": [T_ML, PID]}, a, b)
sw = logs({"address": PM, "topics": [T_SWAP, PID]}, a, b)
print("ModifyLiquidity events", len(ml), "swaps", len(sw))
txs = batch([("eth_getTransactionByHash", [x["transactionHash"]]) for x in ml])
for x, t in zip(ml, txs):
    liq = sgn(int(x["data"][2 + 64*2: 2 + 64*3], 16))
    print(" blk", int(x["blockNumber"], 16), "(+%d)" % (int(x["blockNumber"], 16) - a), "liqDelta", liq, "tx from", t["from"], "nonce", int(t["nonce"], 16), "to", t["to"], t["input"][:10])
if sw:
    s = sorted({x["transactionHash"] for x in sw}); print(" swap blocks", int(sw[0]["blockNumber"], 16), "->", int(sw[-1]["blockNumber"], 16), "distinct swap txs", len(s))
