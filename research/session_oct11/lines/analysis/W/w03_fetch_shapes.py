"""fetch the picked transactions in full (and their receipts for one buy and one sell per shape) -> w03_txs.json"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
P = json.load(open("w02_pick.json"))
hs = sorted({x["hash"] for k, v in P for x in v})
txs = rpc.batch("eth_getTransactionByHash", [[h] for h in hs])
rc_h = sorted({v[0]["hash"] for k, v in P})
rcs = rpc.batch("eth_getTransactionReceipt", [[h] for h in rc_h], n=10)
json.dump({"txs": dict(zip(hs, txs)), "receipts": dict(zip(rc_h, rcs))}, open("w03_txs.json", "w"))
print(len(hs), sum(1 for t in txs if t), len(rc_h), sum(1 for r in rcs if r), rpc.STATS)
