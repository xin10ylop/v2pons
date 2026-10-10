#!/usr/bin/env python3
"""Swap + ModifyLiquidity logs for the recent (post-census) PM1444-family pools over [launch, launch + 6000] (or head) -> recentlogs.pkl,
same tuple shape as others/cache_plogs.pkl: (bn, logIndex, topic0, topic2, data, txhash)."""
import sys, os, pickle, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, logs, PM, T_SWAP, T_ML
RC = json.load(open(os.path.join(HERE, "recent.json"))); head = int(rpc("eth_blockNumber", []), 16); SPAN = 6000
pools = sorted((x["b0"], x["pid"]) for x in RC["launches"] if x["fam"] in ("v3.0", "v5.0", "v2.433"))
P = os.path.join(HERE, "recentlogs.pkl"); out = pickle.load(open(P, "rb")) if os.path.exists(P) else {"head": head, "plogs": {}}
out["head"] = head
groups = []; g = []
for b, p in pools:
    if g and (b - g[0][0] > 6000 or len(g) >= 40): groups.append(g); g = []
    g.append((b, p))
if g: groups.append(g)
for gi, g in enumerate(groups):
    a = g[0][0]; z = min(g[-1][0] + SPAN, head); ids = [p for _, p in g]
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, z); win = {p: b for b, p in g}; o = {p: [] for p in ids}
    for x in ls:
        p = x["topics"][1]; bn = int(x["blockNumber"], 16)
        if win[p] <= bn <= win[p] + SPAN: o[p].append((bn, int(x["logIndex"], 16), x["topics"][0], x["topics"][2], x["data"], x["transactionHash"]))
    out["plogs"].update(o); print(gi, len(groups), len(ls), flush=True)
pickle.dump(out, open(P, "wb")); print("done", len(out["plogs"]), sum(len(v) for v in out["plogs"].values()))
