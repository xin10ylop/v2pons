"""Receipts of every census-known swap tx (first 8 swaps per pool) and the launch txs of both assigned families, cached; the hooks' code sizes."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch, rpc
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(os.path.join(HERE, "pids.json")))
P = load_pools(); T = load_txs(); E = load_events(set(ids["F1"] + ids["F2"]))
want = []
for fam in ("F1", "F2"):
    for pid in ids[fam]:
        want.append(P[pid]["launch_tx"])
        for s in E[pid]["swaps"]:
            if s["tx"] in T: want.append(s["tx"])
want = list(dict.fromkeys(want))
CACHE = os.path.join(HERE, "hookfee_rcpts.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
miss = [h for h in want if h not in R]
print("want", len(want), "miss", len(miss))
if miss:
    R.update(zip(miss, batch([("eth_getTransactionReceipt", [h]) for h in miss])))
hooks = sorted(set(P[x]["hooks"] for x in ids["F1"] + ids["F2"]))
if "_code" not in R:
    codes = batch([("eth_getCode", [a, "latest"]) for a in hooks[:3] + ["0xdbebc6a7b2a38197932b6e01fb0e57e71d726aec"]])
    R["_code"] = {a: c for a, c in zip(hooks[:3] + ["0xdbebc6a7b2a38197932b6e01fb0e57e71d726aec"], codes)}
json.dump(R, open(CACHE, "w"))
print({a: len(c) // 2 - 1 for a, c in R["_code"].items()})
