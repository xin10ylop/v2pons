#!/usr/bin/env python3
"""Every strict-fingerprint launch after the census (cache_post_launch.pkl, refreshed by post_check.py): its pool's Swap/ModifyLiquidity logs over
[b0, b0 + 400] fetched fresh (not the sibling cache), the pull offset, the real buys before it, and any swap whose sender is not the
Universal Router. Prints the early-pull rate by hour (UTC).   python3 recent_pulls.py   (cache vbot/cache_recent_logs.pkl)"""
import sys, os, json, pickle, collections, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, SCR); sys.path.insert(0, HERE)
from chain import rpc, logs, batch, PM, T_SWAP, T_ML
from vbot_feed import launch_of
def s(x): return x - (1 << 256) if x >> 255 else x
def s128(x):
    x = s(x); return x - (1 << 128) if x >= (1 << 127) else x
PC = pickle.load(open(os.path.join(HERE, "cache_post_launch.pkl"), "rb"))
CP = os.path.join(HERE, "cache_recent_logs.pkl"); C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
head = int(rpc("eth_blockNumber", []), 16)
L = []
for l in PC["inits"]:
    t = PC["tx"].get(l["transactionHash"])
    if t and launch_of((t["to"] or "")[2:].lower(), int(t["value"], 16), bytes.fromhex(t["input"][2:])):
        L.append((int(l["blockNumber"], 16), l["topics"][1]))
L.sort()
need = [(b, p) for b, p in L if p not in C and b + 400 <= head]
for i in range(0, len(need), 30):
    g = need[i:i + 30]
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p for _, p in g]]}, g[0][0], g[-1][0] + 400)
    w = {p: b for b, p in g}
    for p in w: C[p] = []
    for x in ls:
        p = x["topics"][1]; bn = int(x["blockNumber"], 16)
        if w[p] <= bn <= w[p] + 400: C[p].append((bn, int(x["logIndex"], 16), x["topics"][0], x["topics"][2], x["data"], x["transactionHash"]))
    pickle.dump(C, open(CP, "wb")); time.sleep(0.2)
ts = {}
blks = sorted({b for b, p in L})
for i in range(0, len(blks), 50):
    for b, r in zip(blks[i:i + 50], batch([("eth_getBlockByNumber", [hex(b), False]) for b in blks[i:i + 50]])): ts[b] = int(r["timestamp"], 16)
byh = collections.defaultdict(list)
for b, p in L:
    if p not in C: continue
    pull = None; buys = []; other = 0
    for bn, li, t0, snd, d, th in sorted(C[p], key=lambda x: (x[0], x[1])):
        if t0 == T_ML and s(int(d[130:194], 16)) < 0 and pull is None: pull = bn - b
        if t0 == T_SWAP and pull is None:
            if snd[-40:] != "8876789976decbfcbbbe364623c63652db8c0904": other += 1
            if s128(int(d[2:66], 16)) <= -2 * 10**14: buys.append(bn - b)
    byh[time.strftime("%m-%d %H", time.gmtime(ts[b]))].append((pull, buys, other))
print("hour (UTC)  launches  pulled<=40  pulled before a 2nd real buy  pools with a non-UR swap before the pull")
for h in sorted(byh):
    v = byh[h]
    print(f"{h}h   {len(v):4d}   {sum(1 for p, b, o in v if p is not None and p <= 40):4d}   {sum(1 for p, b, o in v if p is not None and (len(b) < 2 or p <= b[1])):4d}   {sum(1 for p, b, o in v if o):4d}")
print("launches", len(L), "with logs", sum(1 for b, p in L if p in C), "head", head, time.strftime("%m-%d %H:%M", time.gmtime(int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16))))
