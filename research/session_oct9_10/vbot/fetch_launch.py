#!/usr/bin/env python3
"""Fetch the full launch transaction (with input) of every census pool launched by a call to the v4 PositionManager
(0x58daec31...), 3,386 pools; cache vbot/cache_launch.pkl {tx hash: tx}."""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, SCR)
from chain import batch
PMGR = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
CP = os.path.join(HERE, "cache_launch.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
need = sorted({r["tx"] for r in R if (r["to"] or "").lower() == PMGR} - set(C))
print("to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: C[h] = t
    if i % 500 == 0:
        pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print(i, len(C), flush=True)
    time.sleep(0.1)
pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print("done", len(C))
