#!/usr/bin/env python3
"""Fetch for the whole original-launcher family (94 pools, Oct 8 00:00 - Oct 9 14:48): the transaction of every real buy (>= 0.0002 ETH
into the pool) up to the pull (or launch + 3000), every pull transaction, every deployer's nonce now. Cache: cache_famtx.pkl (reads the
shared others/cache_crowdtx.pkl, never writes it)."""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, SCR)
from chain import rpc, batch, T_SWAP, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = [json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))]
o = [r for r in R if r["ours"] == "orig"]
pl = pickle.load(open(os.path.join(HERE, "..", "cache_plogs.pkl"), "rb"))
shared = pickle.load(open(os.path.join(HERE, "..", "cache_crowdtx.pkl"), "rb"))
CP = os.path.join(HERE, "cache_famtx.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {"tx": {}, "pull": {}, "nonce": {}}
def keep(t): return {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10],
                     "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16)}
need = []
for r in o:
    pb = r["b0"] + r["pull"] if r["pull"] is not None else r["b0"] + 3000
    for bn, li, t0, snd, d, th in pl[r["pid"]]:
        if t0 == T_SWAP and s128(W(d, 0)) <= -2 * 10**14 and bn <= pb and th not in C["tx"]:
            if th in shared and "gas" in shared[th]: C["tx"][th] = shared[th]
            else: need.append(th)
need = sorted(set(need)); print("buy txs to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]; res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, res):
        if t: C["tx"][h] = keep(t)
    if i % 500 == 0:
        pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print(i, flush=True)
    time.sleep(0.2)
pt = [r["pull_tx"] for r in o if r.get("pull_tx") and r["pull_tx"] not in C["pull"]]
for h, t in zip(pt, batch([("eth_getTransactionByHash", [h]) for h in pt])):
    if t: C["pull"][h] = keep(t) | {"block": int(t["blockNumber"], 16)}
deps = sorted({r["from"].lower() for r in o} - set(C["nonce"]))
for a, n in zip(deps, batch([("eth_getTransactionCount", [a, "latest"]) for a in deps])):
    C["nonce"][a] = int(n, 16) if n else None
C["nonce_head"] = int(rpc("eth_blockNumber", []), 16)
pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
print("done tx", len(C["tx"]), "pulls", len(C["pull"]), "deployers", len(C["nonce"]))
