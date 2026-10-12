"""the transaction of every Swap in each line pool from the launch up to its first Burn (or the window's end, launch + 3000), and of the
first Burn: from, to, selector, calldata length, value, nonce, gas (input kept when <= 1,000 bytes) -> r03_txs_cache.jsonl (resumable)."""
from common import *
import rpc
L = json.load(open(J("r01_launches.json")))
E = {x["pool"]: x for x in jl(J("r02_events_cache.jsonl"))}
want = []
for x in L:
    e = E.get(x["pool"])
    if not e: continue
    ls = sorted(e["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    for l in ls:
        if l["topics"][0] in (T_SW, T_BU): want.append(l["transactionHash"])
        if l["topics"][0] == T_BU: break
have = {t["hash"] for t in jl(J("r03_txs_cache.jsonl"))}
todo = sorted(set(want) - have)
print(f"txs wanted {len(set(want))}, cached {len(have)}, to fetch {len(todo)}", flush=True)
f = open(J("r03_txs_cache.jsonl"), "a")
for i in range(0, len(todo), 250):
    ch = todo[i:i + 250]
    rs = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    for h, t in zip(ch, rs):
        if not t: print("missing", h); continue
        inp = t["input"]; n = (len(inp) - 2) // 2
        f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": inp[2:10], "len": n, "value": int(t["value"], 16),
                            "nonce": int(t["nonce"], 16), "gas": int(t["gas"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
                            "input": inp if n <= 1000 else None}) + "\n")
    f.flush()
    if i % 5000 == 0: print(i, rpc.STATS, flush=True)
print("done", rpc.STATS)
