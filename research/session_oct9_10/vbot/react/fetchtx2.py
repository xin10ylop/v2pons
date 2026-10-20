#!/usr/bin/env python3
"""tx behind every Swap log of the recent (post-census) family pools up to min(pull, +600), the pull txs of every pool (census + recent)
and the launch txs of the recent pools -> react/cache_tx2.pkl (same record shape as vbot/cache_tx.pkl)"""
import sys, os, pickle, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from chain import batch
P, TX, M = load(tx=True)
CP = os.path.join(HERE, "cache_tx2.pkl"); T2 = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
def keep(t):
    i = t["input"]
    return {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(i) - 2) // 2, "sel": i[:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16),
            "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
            "input": i if len(i) <= 2 + 2 * 400 else i[:2 + 2 * 200]}
need = []
for v in P.values():
    if v["pull_tx"]: need.append(v["pull_tx"])
    if v["src"] == "recent":
        need.append(v["tx"])
        lim = min(v["pull"] if v["pull"] is not None else 600, 600)
        need += [s["th"] for s in v["sw"] if s["rel"] <= lim]
need = [h for h in dict.fromkeys(need) if h not in TX and h not in T2]
print("to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
        if t: T2[h] = keep(t)
    if i % 2500 == 0: pickle.dump(T2, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print(i, flush=True)
pickle.dump(T2, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print("done", len(T2), flush=True)
