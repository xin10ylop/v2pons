#!/usr/bin/env python3
"""Fetch the transaction behind every Swap / ModifyLiquidity log of the PM1444 families (v3.0, v5.0, v2.433) in the census windows
[launch, launch + 3000] (Swaps only up to the first pull). Priority: logs within +300 first. Cache: vbot/cache_tx.pkl (resumes)."""
import sys, os, pickle, time, json, urllib.request, threading, queue
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import post, T_SWAP
D = pickle.load(open(os.path.join(HERE, "fam.pkl"), "rb"))
CP = os.path.join(HERE, "cache_tx.pkl")
TX = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
sh = pickle.load(open(os.path.join(HERE, "..", "others", "cache_crowdtx.pkl"), "rb"))
def keep(t):
    i = t["input"]
    return {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(i) - 2) // 2, "sel": i[:10], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16),
            "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
            "input": i if len(i) <= 2 + 2 * 400 else i[:2 + 2 * 200]}
pri, rest = [], []
for p, r in D["rows"].items():
    pull = r.get("pull")
    for bn, li, t0, snd, d, th in D["plogs"][p]:
        rel = bn - r["b0"]
        if t0 == T_SWAP and pull is not None and rel > pull: continue
        (pri if rel <= 300 or t0 != T_SWAP else rest).append(th)
seen = set(); order = []
for h in pri + rest:
    if h not in seen and h not in TX: seen.add(h); order.append(h)
print("to fetch", len(order), "cached", len(TX), flush=True)
chunks = [order[i:i + 50] for i in range(0, len(order), 50)]
q = queue.Queue(); [q.put(c) for c in chunks]; lock = threading.Lock(); done = [0]
def worker():
    while True:
        try: ch = q.get_nowait()
        except queue.Empty: return
        try:
            r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [h]} for j, h in enumerate(ch)])
            r = {x["id"]: x.get("result") for x in r}
            with lock:
                for j, h in enumerate(ch):
                    if r.get(j): TX[h] = keep(r[j])
                done[0] += 1
        except Exception as e:
            print("err", e, flush=True); time.sleep(5); q.put(ch)
ths = [threading.Thread(target=worker) for _ in range(3)]; [t.start() for t in ths]
t0 = time.time()
while any(t.is_alive() for t in ths):
    time.sleep(30)
    with lock: pickle.dump(TX, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
    print(f"{done[0]}/{len(chunks)} chunks, {len(TX)} txs, {time.time() - t0:.0f}s", flush=True)
pickle.dump(TX, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP); print("done", len(TX), flush=True)
