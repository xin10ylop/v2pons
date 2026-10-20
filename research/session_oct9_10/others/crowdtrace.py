#!/usr/bin/env python3
"""Where else does our operator's crowd buy? (1) the wallets behind the real buys (>= 0.0002 ETH, first 300 blocks) on every original-launcher
pool; the recurring ones (>= 2 pools). (2) Every token the PoolManager sent to those wallets (ERC-20 Transfer from the PoolManager, i.e. a v4
buy's take) from Oct 8 00:00 to the head. (3) Those tokens mapped to the census pools and their launch families. Writes crowdtrace.json."""
import sys, os, json, pickle, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch, logs, PM, T_SWAP, W, sgn
from eth_utils import keccak
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
START = 82878144; HEAD = int(sys.argv[1]) if len(sys.argv) > 1 else 84238619
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = [json.loads(l) for l in open(os.path.join(HERE, "census.jsonl"))]
plogs = pickle.load(open(os.path.join(HERE, "cache_plogs.pkl"), "rb"))
cache_p = os.path.join(HERE, "cache_crowdtx.pkl")
TX = pickle.load(open(cache_p, "rb"))
orig = [r for r in R if r["ours"] == "orig" and r["logs"]]
need = []
per_pool = {}
for r in orig:
    ths = [th for bn, li, t0, snd, d, th in sorted(plogs[r["pid"]], key=lambda x: (x[0], x[1])) if t0 == T_SWAP and s128(W(d, 0)) <= -2e14 and bn - r["b0"] <= 300]
    per_pool[r["pid"]] = ths[:60]; need += [h for h in ths[:60] if h not in TX]
need = sorted(set(need)); print("orig pools", len(orig), "buy txs to fetch", len(need), flush=True)
for i in range(0, len(need), 50):
    ch = need[i:i + 50]; res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, res):
        if t: TX[h] = {"from": t["from"], "to": t["to"], "inlen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16)}
pickle.dump(TX, open(cache_p, "wb"))
wp = collections.Counter()
for pid, ths in per_pool.items():
    for w in {TX[h]["from"] for h in ths if h in TX}: wp[w] += 1
sig = [TX[h] for ths in per_pool.values() for h in ths if h in TX]
print("buys", len(sig), "wallets", len(wp), "in >= 2 pools", sum(1 for n in wp.values() if n >= 2), "sig 1124/0.02", sum(1 for t in sig if t["inlen"] == 1124 and t["prio"] == 20_000_000), flush=True)
crowd = sorted(w for w, n in wp.items() if n >= 2)
# (2) PoolManager -> crowd wallet token transfers
tok_hits = collections.defaultdict(lambda: collections.Counter())
pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
for i in range(0, len(crowd), 25):
    ws = [pad(w) for w in crowd[i:i + 25]]
    a = START
    while a <= HEAD:
        b = min(a + 199999, HEAD)
        for l in logs({"topics": [T_TR, pad(PM), ws]}, a, b):
            tok_hits[l["address"].lower()]["0x" + l["topics"][2][-40:]] += 1
        a = b + 1
    print("wallet chunk", i, "tokens", len(tok_hits), flush=True)
by_token = {r["token"].lower(): r for r in R}
out = {"crowd_wallets": crowd, "wallet_pools": dict(wp), "tokens": {}}
fam = collections.Counter(); fam_ex = collections.defaultdict(list)
for t, c in tok_hits.items():
    r = by_token.get(t)
    key = ("OURS-" + r["ours"]) if r and r["ours"] else (f"{r['to']}|{r['sel']}|len{r['inlen']}|fee{r['fee']}|ts{r['ts']}" if r else "not an Oct 8-9 v4 ETH pool in the census")
    out["tokens"][t] = {"buys": sum(c.values()), "wallets": len(c), "family": key, "pid": r["pid"] if r else None, "b0": r["b0"] if r else None}
    fam[key] += 1; fam_ex[key].append((t, sum(c.values()), len(c)))
out["families"] = {k: {"tokens": n, "examples": sorted(fam_ex[k], key=lambda x: -x[1])[:6]} for k, n in fam.most_common()}
json.dump(out, open(os.path.join(HERE, "crowdtrace.json"), "w"), indent=1)
for k, n in fam.most_common(30):
    print(n, k, sorted(fam_ex[k], key=lambda x: -x[1])[:3])
