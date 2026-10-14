"""Ethereum: the operator wallet 0x31c8cf1c (got 0.8 ETH from the hub, 8.4807 ETH from 0x8b499c5a): all its transactions since Oct 1."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx, walletx
A = "0x31c8cf1c5edf64777d70727a92a6f46b6b794664"
h, _ = rpcx.head("eth_h"); lo = rpcx.block_at("eth_h", 1790812800)  # Oct 1 00:00 UTC
print("nonce at Oct 1", walletx.nonce("eth_h", A, lo), "bal", walletx.bal("eth_h", A, lo) / 1e18)
n0, n1, T = walletx.txs("eth_h", A, lo, h)
print(A, "nonce", n0, "->", n1)
for t in T:
    r = rpcx.call("eth_h", "eth_getTransactionReceipt", [t["h"]]); t["status"] = r["status"]; t["gas"] = int(r["gasUsed"], 16)
    t["nlogs"] = len(r["logs"]); t["logs"] = [{"a": l["address"], "t": l["topics"], "d": l["data"][:400]} for l in r["logs"][:12]]
    print(" ", time.strftime("%m-%d %H:%M:%S", time.gmtime(t["ts"])), t["b"], "n", t["nonce"], "to", t["to"], "v", t["v"], t["sel"], t["len"], "st", t["status"], "logs", t["nlogs"], t["h"])
json.dump(T, open("c08_treasury_eth.json", "w"), indent=1)
