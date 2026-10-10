"""Log-based profile of wallets: every ERC-20/721 Transfer to/from it and Approval by it in [START, head]; the txs behind them.
Usage: bprof.py START w... -> prof/<w>.json"""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
os.makedirs(D + "prof", exist_ok=True)
START = int(sys.argv[1]); head = int(rpc("eth_blockNumber", []), 16)
for w in sys.argv[2:]:
    w = w.lower(); fn = D + "prof/%s.json" % w
    if os.path.exists(fn): continue
    tw = "0x" + "0" * 24 + w[2:]
    Lg = logs({"topics": [T_TR, None, tw]}, START, head) + logs({"topics": [T_TR, tw]}, START, head) + logs({"topics": [T_AP, tw]}, START, head)
    hs = sorted({l["transactionHash"] for l in Lg})
    txs = {}
    for h, t in zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs])):
        if t: txs[h] = {"bn": int(t["blockNumber"], 16), "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value": int(t["value"], 16), "sel": t["input"][:10], "nonce": int(t["nonce"], 16), "ilen": len(t["input"])}
    ev = [{"tx": l["transactionHash"], "addr": l["address"].lower(), "t0": l["topics"][0], "from": "0x" + l["topics"][1][-40:] if len(l["topics"]) > 1 else None,
           "to": "0x" + l["topics"][2][-40:] if len(l["topics"]) > 2 else None, "data": l["data"][:66], "bn": int(l["blockNumber"], 16)} for l in Lg]
    json.dump({"w": w, "start": START, "head": head, "txs": txs, "ev": ev}, open(fn, "w"))
    mine = sorted(t["nonce"] for t in txs.values() if t["from"] == w)
    print(w, "logs", len(Lg), "txs", len(txs), "sent", len(mine), "nonce", mine[:1], mine[-1:], flush=True)
