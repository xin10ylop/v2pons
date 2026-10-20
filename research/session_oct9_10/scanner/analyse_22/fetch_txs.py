"""fetch the transactions (eth_getTransactionByHash) of every swap of the fee-500/fee-100 2-ETH group and of the first 80 swaps of the
0x0587d47d family that the census did not fetch (it kept the first 8 swaps' txs only). Cached to extra_txs.json; batched 50 per POST."""
import sys, json, os
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
from chain import batch
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
f100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
G1 = F[K[0]]["pids"] + F[f100]["pids"]; G3 = F[K[2]]["pids"]
E = load_events(set(G1 + G3))
want = sorted(set(s["tx"] for x in G1 for s in E[x]["swaps"] if s["tx"] not in T) | set(s["tx"] for x in G3 for s in E[x]["swaps"][:80] if s["tx"] not in T)
           | set(pl["tx"] for x in G1 + G3 for pl in E[x]["pulls"] if pl["tx"] not in T))
OUT = "extra_txs.json"
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
need = [h for h in want if h not in have]
print("want", len(want), "need", len(need))
res = batch([("eth_getTransactionByHash", [h]) for h in need])
for h, r in zip(need, res):
    if r: have[h] = {"hash": h, "from": r["from"].lower(), "to": (r["to"] or "").lower() or None, "nonce": int(r["nonce"], 16), "value_wei": int(r["value"], 16),
                     "selector": r["input"][2:10], "calldata_len": (len(r["input"]) - 2) // 2, "input": r["input"] if len(r["input"]) < 4098 else r["input"][:1026],
                     "bn": int(r["blockNumber"], 16), "ti": int(r["transactionIndex"], 16)}
json.dump(have, open(OUT, "w"))
print("have", len(have), "missing", sum(1 for h in want if h not in have))
