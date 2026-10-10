"""Skeptic f2276/100: receipts of a few crowd buys, crowd sells and pulls (who receives what: WETH pulls? ETH to whom?)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import batch
pools, TX = load_sample()
pick = []
pl = [p for p in pools if p["src"] == "fresh"][0]
b = [s for s in pl["swaps"] if s["crowd"] and s["buy"]][:3]; se = [s for s in pl["swaps"] if s["crowd"] and not s["buy"]][:3]
pu = [p["pulls"][0] for p in pools if p["pulls"]][:3]
hs = [s["tx"] for s in b + se] + [x["tx"] for x in pu]
p = os.path.join(D, "receipts.json")
R = json.load(open(p)) if os.path.exists(p) else {}
need = [h for h in hs if h not in R]
if need:
    for h, r in zip(need, batch([("eth_getTransactionReceipt", [h]) for h in need])): R[h] = r
    json.dump(R, open(p, "w"))
for h in hs:
    r = R[h]; t = TX[h]
    print("==", h[:12], "from", t["from"], "to", t["to"], "value", t["value"], "status", r["status"], "gasUsed", int(r["gasUsed"], 16), "logs", len(r["logs"]))
    for l in r["logs"]:
        print("   ", l["address"], l["topics"][0][:12], [x[-40:] for x in l["topics"][1:]], l["data"][:200])
for s in se[:1]:
    inp = s["input"]; print("sell input"); [print("  ", i, inp[10 + 64 * i: 10 + 64 * (i + 1)]) for i in range((len(inp) - 10) // 64)]
for x in pu[:1]:
    inp = x["input"]; print("pull input", len(inp)); [print("  ", i, inp[10 + 64 * i: 10 + 64 * (i + 1)]) for i in range((len(inp) - 10) // 64)]
