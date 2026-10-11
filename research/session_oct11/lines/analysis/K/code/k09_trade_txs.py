"""the transactions behind a sample of the busy curve's buy/sell/9f4c events: to, selector, value, input words"""
import json, collections
from krpc import *
D = json.load(open(os.path.join(DATA, "curve_e8e3_logs.json"))); L = D["logs"]; s = D["s"]
pick = {}
for l in L:
    t = l["topics"][0][:10]
    pick.setdefault(t, [])
    if len(pick[t]) < 4: pick[t].append(l["transactionHash"])
hs = list(dict.fromkeys(h for v in pick.values() for h in v))
T = batch([("eth_getTransactionByHash", [h]) for h in hs]); R = batch([("eth_getTransactionReceipt", [h]) for h in hs])
json.dump({"txs": T, "rcpts": R}, open(os.path.join(DATA, "curve_e8e3_txs.json"), "w"))
for t, r in zip(T, R):
    inp = t["input"]; ws = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
    print(t["hash"][:12], "from", t["from"][:10], "to", t["to"], "val", int(t["value"], 16), "sel", inp[:10], "gasUsed", int(r["gasUsed"], 16), "gp", int(r["effectiveGasPrice"], 16), "L1fee?", r.get("l1Fee"), r.get("gasUsedForL1"))
    print("     words", [int(w, 16) if int(w, 16) < 2**100 else "0x" + w[24:] for w in ws[:8]])
    for l in r["logs"]:
        print("       ", l["address"][:10], l["topics"][0][:10], [A(x)[:10] for x in l["topics"][1:]], [W(l["data"], i) for i in range(min(4, (len(l["data"]) - 2) // 64))])
