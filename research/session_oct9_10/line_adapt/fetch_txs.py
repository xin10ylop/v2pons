#!/usr/bin/env python3
"""line_adapt: every swap/ModifyLiquidity tx of the window (to, from, value, calldata words), worker k of n, appended to data/txs_k.jsonl.
Order: the txs in the first 120 blocks after launch first, then the rest.   python3 -I fetch_txs.py k n"""
import sys, os, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
k, n = int(sys.argv[1]), int(sys.argv[2])
P = {p["pid"]: p["b0"] for p in json.load(open(os.path.join(D, "pools.json")))}
E = json.load(open(os.path.join(D, "events.json")))
have = set()
for f in os.listdir(D):
    if f.startswith("txs_") and f.endswith(".jsonl"):
        for line in open(os.path.join(D, f)):
            try: have.add(json.loads(line)["hash"])
            except Exception: pass
if os.path.exists(os.path.join(D, "txs.json")):
    old = json.load(open(os.path.join(D, "txs.json")))
    if k == 0:
        with open(os.path.join(D, "txs_old.jsonl"), "a") as fo:
            for h, t in old.items():
                if h not in have: fo.write(json.dumps(dict(t, hash=h)) + "\n")
    have |= set(old)
early, late = [], []
for pid, L in E.items():
    for c in L:
        (early if c["bn"] - P[pid] <= 120 else late).append(c["tx"])
need = [h for h in dict.fromkeys(early + late) if h not in have]
need = [h for i, h in enumerate(need) if i % n == k]
print(time.strftime("%H:%M:%S"), "worker", k, "need", len(need), flush=True)
fo = open(os.path.join(D, f"txs_{k}.jsonl"), "a")
for i in range(0, len(need), 250):
    ch = need[i:i + 250]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
        if t is None: continue
        inp = t["input"]
        fo.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "sel": inp[2:10],
                             "clen": (len(inp) - 2) // 2, "input": inp[:2 + 64 * 16 + 8], "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
                             "gasPrice": int(t.get("gasPrice") or "0x0", 16), "maxPrio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
                             "gas": int(t["gas"], 16)}) + "\n")
    fo.flush()
    if (i // 250) % 8 == 0: print(time.strftime("%H:%M:%S"), "worker", k, i + len(ch), "/", len(need), flush=True)
print(time.strftime("%H:%M:%S"), "worker", k, "done", flush=True)
