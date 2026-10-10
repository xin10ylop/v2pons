#!/usr/bin/env python3
"""Every ModifyLiquidity log of every PM1444-family pool (census + recent launches) from its launch to the head -> mlall.pkl {pid: [(bn, li, liqDelta, tx)]}"""
import sys, os, pickle, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, logs, PM, T_ML, W, sgn
D = pickle.load(open(os.path.join(HERE, "fam.pkl"), "rb")); RC = json.load(open(os.path.join(HERE, "recent.json")))
pools = [(r["b0"], p) for p, r in D["rows"].items()] + [(x["b0"], x["pid"]) for x in RC["launches"] if x["fam"] in ("v3.0", "v5.0", "v2.433")]
pools.sort(); head = int(rpc("eth_blockNumber", []), 16); out = {p: [] for _, p in pools}
for i in range(0, len(pools), 100):
    g = pools[i:i + 100]; ids = [p for _, p in g]
    for x in logs({"address": PM, "topics": [T_ML, ids]}, g[0][0], head):
        out[x["topics"][1]].append((int(x["blockNumber"], 16), int(x["logIndex"], 16), sgn(W(x["data"], 2)), x["transactionHash"]))
    print(i, len(pools), flush=True)
pickle.dump({"head": head, "ml": out}, open(os.path.join(HERE, "mlall.pkl"), "wb"))
