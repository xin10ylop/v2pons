#!/usr/bin/env python3
"""Verifier step 3 fetch: for a random sample of PM1444 v3.0 pools (plus every pool the hold-30 paper marks pulled or losing) the
transaction behind every swap of >= 0.0002 ETH (buy or sell) from the launch to the pull (or launch + 600), and the pull tx.
Reads the shared caches, writes only verify/cache_v3tx.pkl.   python3 v3_fetch.py"""
import sys, os, json, pickle, random, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR)
from chain import batch, T_SWAP, T_ML, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
PL = pickle.load(open(os.path.join(HERE, "..", "cache_plogs.pkl"), "rb"))
SH = pickle.load(open(os.path.join(HERE, "..", "cache_crowdtx.pkl"), "rb"))
V2 = json.load(open(os.path.join(HERE, "v2_price.json")))
fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
pids = sorted(p for p, r in R.items() if r["logs"] and fam(r))
random.seed(5)
samp = set(random.sample(pids, 150)) | {p for p, ret, why, send in V2["v3"]["per_pool_hold30"] if why == "pulled" or ret < 0}
CP = os.path.join(HERE, "cache_v3tx.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {"tx": {}, "samp": []}
C["samp"] = sorted(samp)
need = set()
for p in samp:
    r = R[p]; end = r["b0"] + (r["pull"] if r.get("pull") is not None and r["pull"] <= 600 else 600)
    for bn, li, t0, snd, d, th in PL[p]:
        if bn > end: continue
        if t0 == T_SWAP and abs(s128(W(d, 0))) >= 2 * 10**14: need.add(th)
        if t0 == T_ML and sgn(W(d, 2)) < 0: need.add(th)
need = sorted(need - set(C["tx"]))
print("sample", len(samp), "txs to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: C["tx"][h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10], "value": int(t["value"], 16) / 1e18,
                            "nonce": int(t["nonce"], 16), "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16)}
    if i % 1000 == 0:
        pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print(i, flush=True)
    time.sleep(0.15)
pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
print("done", len(C["tx"]))
