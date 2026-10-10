#!/usr/bin/env python3
"""Pulls beyond the tx-covered window: fetch the txs of every swap in the 25 blocks before each such pull, then classify the pull as
REACTIVE (an outsider buy in those 25 blocks; >= 3e-5 or smaller) or not. Adds to react/cache_tx3.pkl."""
import sys, os, pickle, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from rpc2 import batch
P, TX, M = load(); CP = os.path.join(HERE, "cache_tx3.pkl"); T3 = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
TX.update(T3)
def keep(t):
    i = t["input"]
    return {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(i) - 2) // 2, "sel": i[:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16),
            "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "input": i[:202]}
need = []
for v in P.values():
    if v["pull"] is None or v["pull"] <= COV[v["src"]] or v["pull"] > v["span"]: continue
    need += [s["th"] for s in v["sw"] if v["pull"] - 25 <= s["rel"] <= v["pull"] and s["th"] not in TX]
need = sorted(set(need)); print("fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
        if t: T3[h] = keep(t)
pickle.dump(T3, open(CP, "wb")); TX.update(T3)
BOTW, cls = classifier(TX)
for fam in ("v3.0", "v5.0", "v2.433"):
    c = collections.Counter(); lt = collections.defaultdict(list)
    for v in P.values():
        if v["fam"] != fam or v["pull"] is None or v["pull"] <= COV[v["src"]]: continue
        if v["pull"] > v["span"]: c["pull beyond log window"] += 1; lt["pull beyond log window"].append(v["pull"]); continue
        big = small = False
        for s in v["sw"]:
            if v["pull"] - 25 <= s["rel"] <= v["pull"] and s["eth"] > 0:
                k, t = cls(v, s)
                if k == "out": big |= s["eth"] >= 3e-5; small |= s["eth"] < 3e-5
        k = "outsider buy >= 3e-5 within 25" if big else ("only a small (<3e-5) outsider buy within 25" if small else "no outsider buy within 25")
        c[k] += 1; lt[k].append(v["pull"])
    print(fam, dict(c))
    for k, xs in lt.items():
        xs.sort(); print(f"    {k}: lifetime q0/10/25/50/75/90/100 {[xs[int(a*(len(xs)-1))] for a in (0,.1,.25,.5,.75,.9,1)]}")
