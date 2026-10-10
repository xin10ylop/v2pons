"""Who traded in the pool created by a launch tx: Swap logs (PoolManager) for the pid between launch and `until`, tx senders and ETH amounts.
Usage: poolbuyers.py launch_tx until_block"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
h, until = sys.argv[1], int(sys.argv[2])
r = rpc("eth_getTransactionReceipt", [h])
pid = [l["topics"][1] for l in r["logs"] if l["address"].lower() == PM and l["topics"][0] == T_INIT][0]
bn = int(r["blockNumber"], 16)
sw = []
for a in range(bn, until + 1, 30000): sw += logs({"address": PM, "topics": [T_SWAP, pid]}, a, min(until, a + 29999))
ml = []
for a in range(bn, until + 1, 30000): ml += logs({"address": PM, "topics": [T_ML, pid]}, a, min(until, a + 29999))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in sw])
per = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
for l, t in zip(sw, txs):
    a0 = sgn(W(l["data"], 0)); f = t["from"].lower()
    per[f][0] += 1; per[f][3] = int(t["nonce"], 16)
    if a0 < 0: per[f][1] += -a0 / 1e18     # ETH paid in (amount0 negative = into pool from swapper)
    else: per[f][2] += a0 / 1e18
print("pid", pid, "launch", bn, "swaps", len(sw), "liquidity events", [(int(x["blockNumber"], 16), sgn(W(x["data"], 2)) / 1e18) for x in ml])
tot_in = sum(v[1] for v in per.values()); tot_out = sum(v[2] for v in per.values())
print(f"traders {len(per)}; ETH in {tot_in:.4f}, ETH out {tot_out:.4f}")
for f, v in sorted(per.items(), key=lambda x: -x[1][1])[:40]: print(f, "swaps", v[0], f"in {v[1]:.4f} out {v[2]:.4f}", "nonce", v[3])
json.dump({"pid": pid, "per": per}, open("pool_%s.json" % h[:12], "w"))
