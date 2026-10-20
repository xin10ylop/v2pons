#!/usr/bin/env python3
"""Crowd fingerprint per family: for a sample of each family's pools, the transactions behind the real buys (>= 0.0002 ETH) in the first
300 blocks: the buyer wallet, the contract called, the calldata length, the priority fee. Compared with our operator's crowd (the original
launcher's pools). Writes crowd.json."""
import sys, os, json, pickle, random, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch, T_SWAP, W, sgn
random.seed(7)
R = [json.loads(l) for l in open(os.path.join(HERE, "census.jsonl"))]
plogs = pickle.load(open(os.path.join(HERE, "cache_plogs.pkl"), "rb"))
F = json.load(open(os.path.join(HERE, "families.json")))
def tier(f): return "sub1%" if f < 10000 else ("1%" if f == 10000 else ">1%")
cnt_to = collections.Counter(r["to"] or "none" for r in R)
def fam(r):
    if r["ours"]: return f"OURS-{r['ours']}"
    to = r["to"] or "none"; c = to if cnt_to[to] >= 3 else f"percontract:{(r['codesize'] or 0) // 100 * 100}"
    return f"{c}|{r['sel']}|len{r['inlen']}|{tier(r['fee'])}|ts{r['ts']}|v{round(r['value'] or 0, 3)}"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
G = collections.defaultdict(list)
for r in R:
    if r["logs"] and r.get("n_real300", 0) > 0: G[fam(r)].append(r)
cache_p = os.path.join(HERE, "cache_crowdtx.pkl")
try: TX = pickle.load(open(cache_p, "rb"))
except Exception: TX = {}
plan = {}
for k, v in G.items():
    if len(v) < 3 and not k.startswith("OURS"): continue
    m = 40 if k == "OURS-orig" else 10
    samp = random.sample(v, min(m, len(v))); plan[k] = []
    for r in samp:
        ev = sorted(plogs[r["pid"]], key=lambda x: (x[0], x[1]))
        buys = [(bn - r["b0"], -s128(W(d, 0)) / 1e18, th) for bn, li, t0, snd, d, th in ev if t0 == T_SWAP and s128(W(d, 0)) <= -2e14 and bn - r["b0"] <= 300]
        plan[k].append((r["pid"], buys[:10]))
need = sorted({th for k in plan for pid, b in plan[k] for _, _, th in b} - set(TX))
print("families", len(plan), "txs to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]; res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, res):
        if t: TX[h] = {"from": t["from"], "to": t["to"], "inlen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16)}
    if i % 1000 == 0: pickle.dump(TX, open(cache_p, "wb")); print("tx", i, flush=True)
pickle.dump(TX, open(cache_p, "wb"))
ours_w = {TX[th]["from"] for pid, b in plan.get("OURS-orig", []) for _, _, th in b if th in TX}
out = {}
for k, smp in plan.items():
    txs = [TX[th] for pid, b in smp for _, _, th in b if th in TX]
    if not txs: continue
    w = collections.Counter(t["from"] for t in txs)
    pools_per_w = collections.Counter();
    for pid, b in smp:
        for x in {TX[th]["from"] for _, _, th in b if th in TX}: pools_per_w[x] += 1
    out[k] = {"pools": len(smp), "buys": len(txs), "wallets": len(w), "recurring_wallets(>=2 pools)": sum(1 for x, n in pools_per_w.items() if n >= 2),
              "share_ours_crowd": round(sum(1 for t in txs if t["from"] in ours_w) / len(txs), 3), "wallets_shared_with_ours": len(set(w) & ours_w),
              "to": collections.Counter(t["to"] for t in txs).most_common(3), "inlen": collections.Counter(t["inlen"] for t in txs).most_common(3),
              "prio_gwei": collections.Counter(round(t["prio"] / 1e9, 4) for t in txs).most_common(3), "buyer_nonce_med": st.median(t["nonce"] for t in txs),
              "sig_1124_002": round(sum(1 for t in txs if t["inlen"] == 1124 and t["prio"] == 20_000_000) / len(txs), 3)}
json.dump(out, open(os.path.join(HERE, "crowd.json"), "w"), indent=1)
for k, v in sorted(out.items(), key=lambda x: -x[1]["share_ours_crowd"]):
    print(k[:95], v["pools"], v["buys"], "wallets", v["wallets"], "recur", v["recurring_wallets(>=2 pools)"], "ours-share", v["share_ours_crowd"], "shared", v["wallets_shared_with_ours"], "sig", v["sig_1124_002"], v["inlen"][:2], v["prio_gwei"][:2])
