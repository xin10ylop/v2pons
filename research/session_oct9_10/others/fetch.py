#!/usr/bin/env python3
"""Census fetch: every v4 ETH pool (Initialize, currency0 = 0) from Oct 8 00:00 UTC to the head; its launch tx; the launch contract's code
hash; the pool's own Swap + ModifyLiquidity logs over [launch, launch + SPAN]. Stages cache to others/cache_*.pkl (rerun resumes).

    python3 fetch.py [head]
"""
import sys, os, json, time, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, post, batch, logs, PM, T_INIT, T_SWAP, T_ML
from eth_utils import keccak

START = 82878144; SPAN = 3000
head = int(sys.argv[1]) if len(sys.argv) > 1 else int(rpc("eth_blockNumber", []), 16)
C = lambda n: os.path.join(HERE, f"cache_{n}.pkl")
def load(n, d):
    try: return pickle.load(open(C(n), "rb"))
    except Exception: return d
def save(n, v):
    pickle.dump(v, open(C(n) + ".tmp", "wb")); os.replace(C(n) + ".tmp", C(n))

# A: Initialize logs
inits = load("inits", {"to": START - 1, "logs": []})
end = head - SPAN if len(sys.argv) > 2 else head      # pools whose window is complete only, if asked
if inits["to"] < end:
    a = inits["to"] + 1
    while a <= end:
        b = min(a + 99999, end); ls = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b)
        inits["logs"] += ls; inits["to"] = b; a = b + 1; save("inits", inits); print("inits", b, len(inits["logs"]), flush=True)
L = inits["logs"]; print("pools", len(L), flush=True)

# B: launch txs
txs = load("txs", {})
need = sorted({l["transactionHash"] for l in L} - set(txs))
for i in range(0, len(need), 50):
    ch = need[i:i + 50]; r = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, r):
        if t: txs[h] = {k: t.get(k) for k in ("from", "to", "nonce", "value", "gasPrice", "maxPriorityFeePerGas", "blockNumber", "transactionIndex")} | {"input4": t["input"][:10], "inlen": (len(t["input"]) - 2) // 2}
    if i % 1000 == 0: save("txs", txs); print("txs", i, len(need), flush=True)
save("txs", txs)

# B2: contract-creation launches -> receipt contractAddress
rcs = load("rcs", {})
need = [h for h, t in txs.items() if t["to"] is None and h not in rcs]
for i in range(0, len(need), 20):
    ch = need[i:i + 20]; r = batch([("eth_getTransactionReceipt", [h]) for h in ch])
    for h, x in zip(ch, r):
        if x: rcs[h] = {"contractAddress": x.get("contractAddress"), "gasUsed": x.get("gasUsed"), "status": x.get("status")}
save("rcs", rcs)

# C: code hash of every launch contract (latest state; no archive)
codes = load("codes", {})
tos = sorted({t["to"] for t in txs.values() if t["to"]} - set(codes))
for i in range(0, len(tos), 20):
    ch = tos[i:i + 20]; r = batch([("eth_getCode", [a, "latest"]) for a in ch])
    for a, c in zip(ch, r):
        if c is not None: codes[a] = {"hash": keccak(bytes.fromhex(c[2:])).hex() if len(c) > 2 else None, "size": (len(c) - 2) // 2}
    if i % 200 == 0: save("codes", codes); print("codes", i, len(tos), flush=True)
save("codes", codes)

# D: pool logs, grouped: one getLogs per group of up to 40 pools launched within 6000 blocks, topics[1] = the group's pool ids
plogs = load("plogs", {})
pools = sorted(((int(l["blockNumber"], 16), l["topics"][1]) for l in L), key=lambda x: x[0])
todo = [(b, p) for b, p in pools if p not in plogs and b + SPAN <= head]
groups = []; g = []
for b, p in todo:
    if g and (b - g[0][0] > 6000 or len(g) >= 40): groups.append(g); g = []
    g.append((b, p))
if g: groups.append(g)
t0 = time.time()
for gi, g in enumerate(groups):
    a = g[0][0]; z = g[-1][0] + SPAN; ids = [p for _, p in g]
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, z)
    win = {p: b for b, p in g}; out = {p: [] for p in ids}
    for x in ls:
        p = x["topics"][1]; bn = int(x["blockNumber"], 16)
        if p in win and win[p] <= bn <= win[p] + SPAN:
            out[p].append((bn, int(x["logIndex"], 16), x["topics"][0], x["topics"][2], x["data"], x["transactionHash"]))
    plogs.update(out)
    if gi % 20 == 0:
        save("plogs", plogs); print(f"plogs group {gi}/{len(groups)} pools {len(plogs)} {time.time() - t0:.0f}s", flush=True)
save("plogs", plogs)
print("done; head", head, "pools", len(L), "with logs", len(plogs))
