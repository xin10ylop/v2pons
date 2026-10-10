"""Fetch the liquidity-add transactions of the PoolManager-initialize family (their launch is two transactions: PM.initialize, then a
POSM mint some blocks later). Small: one tx per pool (192), batched 50 per POST, cached to adds_txs.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common import *
from chain import batch
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
out_path = os.path.join(HERE, "adds_txs.json")
cache = json.load(open(out_path)) if os.path.exists(out_path) else {}
pids = load_families()[KEY]["pids"]
E = load_events(set(pids))
hs = sorted({E[p]["adds"][0]["tx"] for p in pids if E.get(p) and E[p]["adds"]} - set(cache))
print("to fetch", len(hs))
res = batch([("eth_getTransactionByHash", [h]) for h in hs])
for h, r in zip(hs, res):
    if r: cache[h] = {"from": r["from"].lower(), "to": (r["to"] or "").lower(), "value": int(r["value"], 16), "nonce": int(r["nonce"], 16),
                      "sel": r["input"][2:10], "len": (len(r["input"]) - 2) // 2, "bn": int(r["blockNumber"], 16), "ti": int(r["transactionIndex"], 16),
                      "input": r["input"] if len(r["input"]) < 6000 else r["input"][:6000]}
json.dump(cache, open(out_path, "w"))
print("cached", len(cache))
