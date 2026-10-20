import sys, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch
hs = sys.argv[1:]
out = batch([("eth_getTransactionReceipt", [h]) for h in hs])
for h, r in zip(hs, out):
    print("==", h, "status", r["status"], "gas", int(r["gasUsed"], 16), "from", r["from"], "to", r["to"])
    for l in r["logs"]:
        print("  ", l["address"], [t[:18] for t in l["topics"]], l["data"][:2+64*6])
json.dump(out, open("rcpt_%s.json" % hs[0][:10], "w"))
