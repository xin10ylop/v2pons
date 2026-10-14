"""d14: the operator's footprint: gas price of the launch txs (d01), of the crowd's buys and of the freeze txs; the four freeze wallets'
first and last freeze in the last 3 days and today's nonce; plus a CSV of every stranger (token, buyer) of d10.
-> d14_ops.out, d10_strangers.csv"""
import json, os, sys, csv, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
LS = launches()
g = rpc.batch([("eth_getTransactionByHash", [o["tx"]]) for o in LS])
print("launch txs gas price (gwei):", C.Counter(int(x["result"]["gasPrice"], 16) / 1e9 for x in g if x.get("result")).most_common(4),
      "creator nonce:", C.Counter(int(x["result"]["nonce"], 16) for x in g if x.get("result")).most_common(3))
FZ = json.load(open(os.path.join(D, "d09_freezes.json")))
for op in FZ["ops"]:
    rs = sorted(r["fblk"] for r in FZ["rows"] if r["op"] == op)
    n = int(rpc.call("eth_getTransactionCount", [op, "latest"]), 16)
    print("freeze wallet", op, "freezes", len(rs), "first block", rs[0], "last", rs[-1], "nonce now", n)
print("freeze txs gas price (gwei):", C.Counter(v[3] / 1e9 for v in FZ["freeze_txs"].values()).most_common(3))
T = json.load(open(os.path.join(D, "d10_table.json")))
cols = ["pool", "size", "code", "L", "token", "buyer", "off", "before_dump", "dump_off", "sel", "tx_to", "tx_from", "self", "rtype", "gp_gwei", "bnb", "nbuys",
        "frozen", "freeze_off", "delay", "freeze_op", "moves", "sells", "xfers", "moved_before_freeze", "first_move_off", "first_move_kind", "bal_now", "test_now", "tx"]
with open(os.path.join(D, "d10_strangers.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in T["rows"]: w.writerow([r.get(c) for c in cols])
print("d10_strangers.csv rows", len(T["rows"]))
