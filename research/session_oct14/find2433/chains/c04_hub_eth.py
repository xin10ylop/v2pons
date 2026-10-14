"""The 2.433 hub 0x6c3bd8f6 on Ethereum after the Across fill: every outgoing transaction (nonce binary search), decoded."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx, walletx
A = "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"
h, _ = rpcx.head("eth_h")
n0, n1, T = walletx.txs("eth_h", A, 26176601, h)
print("nonce", n0, "->", n1, "head", h)
for t in T:
    r = rpcx.call("eth_h", "eth_getTransactionReceipt", [t["h"]])
    t["status"] = r["status"]; t["gas"] = int(r["gasUsed"], 16); t["logs"] = [{"a": l["address"], "t": l["topics"], "d": l["data"][:600]} for l in r["logs"]]
    print(time.strftime("%m-%d %H:%M:%S", time.gmtime(t["ts"])), t["b"], "n", t["nonce"], "to", t["to"], "v", t["v"], t["sel"], t["len"], "st", t["status"], t["h"])
    for l in t["logs"]: print("    LOG", l["a"], [x[:66] for x in l["t"]], l["d"][:200])
json.dump(T, open("c04_hub_eth.json", "w"), indent=1)
