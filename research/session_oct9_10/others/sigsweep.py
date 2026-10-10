#!/usr/bin/env python3
"""Signature sweep: the first two real buys of every non-operator pool with >= 2 real buys in its first 300 blocks (not sampled before):
calldata length, priority fee, wallet. Flags our crowd's signature (1,124 bytes, 0.02 gwei) and our crowd's wallets. Writes sigsweep.json."""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch, W, sgn, T_SWAP
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = [json.loads(l) for l in open(os.path.join(HERE, "census.jsonl"))]
plogs = pickle.load(open(os.path.join(HERE, "cache_plogs.pkl"), "rb"))
cache_p = os.path.join(HERE, "cache_crowdtx.pkl"); TX = pickle.load(open(cache_p, "rb"))
crowd = set(json.load(open(os.path.join(HERE, "crowdtrace.json")))["crowd_wallets"])
pp = {}
for r in R:
    if r["ours"] or not r["logs"] or r["n_real300"] < 2: continue
    ths = [th for bn, li, t0, snd, d, th in sorted(plogs[r["pid"]], key=lambda x: (x[0], x[1])) if t0 == T_SWAP and s128(W(d, 0)) <= -2e14 and bn - r["b0"] <= 300]
    pp[r["pid"]] = ths[:2]
need = sorted({h for v in pp.values() for h in v} - set(TX)); print("txs", len(need), flush=True)
for i in range(0, len(need), 25):
    ch = need[i:i + 25]; res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, res):
        if t: TX[h] = {"from": t["from"], "to": t["to"], "inlen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16)}
    if i % 1000 == 0: pickle.dump(TX, open(cache_p, "wb")); print("tx", i, flush=True)
pickle.dump(TX, open(cache_p, "wb"))
hits = []
for pid, ths in pp.items():
    t = [TX[h] for h in ths if h in TX]
    s = sum(1 for x in t if x["inlen"] == 1124 and x["prio"] == 20_000_000); c = sum(1 for x in t if x["from"] in crowd)
    if s or c: hits.append({"pid": pid, "sig": s, "crowd": c, "txs": [(x["from"], x["to"], x["inlen"], x["prio"], x["nonce"]) for x in t]})
json.dump({"pools_checked": len(pp), "hits": hits}, open(os.path.join(HERE, "sigsweep.json"), "w"), indent=1)
by = {r["pid"]: r for r in R}
print("pools checked", len(pp), "with our signature or crowd", len(hits))
fc = collections.Counter((by[h["pid"]]["to"], by[h["pid"]]["sel"], by[h["pid"]]["inlen"], by[h["pid"]]["fee"]) for h in hits)
for k, n in fc.most_common(20): print(n, k)
for h in hits[:15]: print(h["pid"][:14], h["sig"], h["crowd"], h["txs"])
