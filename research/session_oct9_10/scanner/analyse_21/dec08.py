"""router 0xf2251d75 selector 08c1284c (packed calldata): look for amountIn and a minOut field in the buys of deployer 0x841ac064's pools"""
import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
pids = [p["pid"] for p in P.values() if p["launch_from"] == "0x841ac064763c75a6b6b916ef676420d6ffdd281f"]
E = load_events(set(pids)); out = []
for pid in pids:
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        if not t or t["selector"] != "08c1284c": continue
        h = (t.get("input") or t["input512"])[10:]
        body = h[64 * 2:]   # after offset + length words
        out.append({"pid": pid[:12], "side": "buy" if s["a0"] < 0 else "sell", "value_eth": t["value_eth"], "a0": s["a0"], "a1": s["a1"], "from": t["from"], "body": body[:200]})
for o in out: print(o["pid"], o["side"], o["value_eth"], o["a0"], o["a1"], o["from"][:10]); print("    ", o["body"])
json.dump(out, open("dec08.json", "w"), indent=1)
