"""own fetch: the transaction of every swap of each line pool from the launch to + MAXOFF (default 80: everything that can hold a position at our
cap), and of the first Burn (the pull) when it is within the fetched window. Stored reduced: from, to, selector, length, value, nonce, block, index;
input kept when <= 600 bytes. -> s03_txs_cache.jsonl (resumable)."""
from common import *
import rpc
MAXOFF = int(sys.argv[1]) if len(sys.argv) > 1 else 80
EXTRA = sys.argv[2] if len(sys.argv) > 2 else None        # a file of extra hashes (one per line) to fetch
L = {x["pool"]: x for x in json.load(open(J("s01_launches.json")))}
T = {t["hash"] for t in jl(J("s03_txs_cache.jsonl"))}
want = set()
for e in jl(J("s02_logs_cache.jsonl")):
    lb = L[e["pool"]]["lb"]
    for c in e["ev"]:
        if c[0] == "s" and c[1] - lb <= MAXOFF: want.add(c[11])
    b = next((c for c in e["ev"] if c[0] == "b" and c[7] > 0), None)
    if b: want.add(b[10])
if EXTRA: want |= {h.strip() for h in open(EXTRA) if h.strip()}
todo = sorted(want - T)
print(f"wanted {len(want)}, cached {len(T)}, to fetch {len(todo)}", flush=True)
f = open(J("s03_txs_cache.jsonl"), "a")
for i in range(0, len(todo), 200):
    ch = todo[i:i + 200]
    for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=20)):
        if not t: print("missing", h); continue
        inp = t["input"]; n = (len(inp) - 2) // 2
        f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": inp[2:10], "len": n, "value": int(t["value"], 16),
                            "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "input": inp if n <= 600 else None}) + "\n")
    f.flush()
    if i % 2000 == 0: print(i, rpc.STATS, flush=True)
f.close(); print("done", rpc.STATS)
