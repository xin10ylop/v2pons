"""Ethereum: the next launch wallet 0x8b499c5a after the hub's sweep; and the 0.8 ETH receiver 0x31c8cf1c around Oct 12."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx, walletx
h, _ = rpcx.head("eth_h"); res = {}
for A, lo in [("0x8b499c5a56d5d0bed60527463bb1de389d6327e1", 26176820)]:
    n0, n1, T = walletx.txs("eth_h", A, lo, h)
    print(A, "nonce", n0, "->", n1)
    for t in T:
        r = rpcx.call("eth_h", "eth_getTransactionReceipt", [t["h"]]); t["status"] = r["status"]; t["gas"] = int(r["gasUsed"], 16); t["gp"] = int(r["effectiveGasPrice"], 16)
        t["nlogs"] = len(r["logs"]); t["logs"] = [{"a": l["address"], "t": l["topics"], "d": l["data"][:300]} for l in r["logs"][:12]]
        print(" ", time.strftime("%m-%d %H:%M:%S", time.gmtime(t["ts"])), t["b"], "n", t["nonce"], "to", t["to"], "v", t["v"], t["sel"], t["len"], "st", t["status"], "gas", t["gas"], "gp %.2f gwei" % (t["gp"] / 1e9), "logs", t["nlogs"], t["h"])
    res[A] = T
json.dump(res, open("c07_next_eth.json", "w"), indent=1)
