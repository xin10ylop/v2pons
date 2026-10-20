"""every ETH pool launched through the original launcher (or call 0x2fcb9108) in [a, b], with its deployer and pull"""
import sys, json
from tr import *
a, b = int(sys.argv[1]), int(sys.argv[2])
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, a, b)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
out = []
for l, t in zip(inits, txs):
    if not t: continue
    if (t["to"] or "").lower() != "0x3194e32622c5d860a0572c74edda99dcfd8fc827" and t["input"][:10] != "0x2fcb9108": continue
    pid = l["topics"][1]; bn = int(l["blockNumber"], 16)
    ml = logs({"address": PM, "topics": [T_ML, pid]}, bn, b)
    pulls = [int(x["blockNumber"], 16) for x in ml if sgn(W(x["data"], 2)) < 0]
    out.append({"pid": pid, "block": bn, "deployer": t["from"].lower(), "nonce": int(t["nonce"], 16), "fee": W(l["data"], 0), "to": (t["to"] or "").lower(), "pull": min(pulls) if pulls else None})
json.dump(out, open("launches_now.json", "w"))
print(len(out), "launches;", sum(1 for x in out if x["pull"]), "pulled; fees:", sorted(x["fee"] for x in out)[:10], "...")
