"""fetch the first-add transaction of every pool of the PoolManager-initialize family (its liquidity comes in a later tx than the Initialize,
so the census has no tx for it). Cached in cache/add_txs.json."""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import batch
from load import *
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "cache", "add_txs.json")
P = load_pools(); T = load_txs()
fam = [p for p in P.values() if p["launch_to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
E = load_events(set(p["pid"] for p in fam))
want = set()
for p in fam:
    e = E.get(p["pid"])
    if e and e["adds"]: want.add(e["adds"][0]["tx"])
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
need = sorted(h for h in want if h not in have and h not in T)
print("want", len(want), "in census", sum(1 for h in want if h in T), "cached", sum(1 for h in want if h in have), "to fetch", len(need))
res = batch([("eth_getTransactionByHash", [h]) for h in need])
for h, r in zip(need, res):
    if r: have[h] = {"hash": h, "from": r["from"].lower(), "to": (r["to"] or "").lower() or None, "nonce": int(r["nonce"], 16), "bn": int(r["blockNumber"], 16),
                     "ti": int(r["transactionIndex"], 16), "value_wei": int(r["value"], 16), "selector": r["input"][2:10], "calldata_len": (len(r["input"]) - 2) // 2,
                     "input": r["input"] if len(r["input"]) < 6000 else r["input"][:6000]}
json.dump(have, open(OUT, "w"))
print("saved", len(have), "missing", sum(1 for h in need if h not in have))
