"""Step 3: the transaction behind every Swap / ModifyLiquidity of the pools (from, to, nonce, value, selector, calldata length, gas price).
Cached in s03_txs_<k>_cache.jsonl, each under 2 MB. Full calldata kept only for swaps in [L, L+700] (for router decoding)."""
import glob
from common import *
d = jload("s01_inits.json"); L = {c["pid"]: c["block"] for c in d["direct"]}
ev = load_events()
early = {r["tx"] for r in ev if r["bn"] <= L[r["pid"]] + 700}
have = set()
for fp in sorted(glob.glob(os.path.join(HERE, "s03_txs_*_cache.jsonl"))):
    for r in jl_load(os.path.basename(fp)): have.add(r["h"])
want = sorted({r["tx"] for r in ev} - have, key=lambda h: (h not in early, h))
print("need", len(want), "have", len(have))
k = len(glob.glob(os.path.join(HERE, "s03_txs_*_cache.jsonl")))
def fname(k): return f"s03_txs_{k:02d}_cache.jsonl"
for i in range(0, len(want), 500):
    ch = want[i:i + 500]
    res = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    rows = []
    for h, t in zip(ch, res):
        if t is None: rows.append(dict(h=h, miss=1)); continue
        r = dict(h=h, f=t["from"].lower(), to=(t.get("to") or "").lower(), n=int(t["nonce"], 16), v=int(t["value"], 16), s=t["input"][:10],
                 il=(len(t["input"]) - 2) // 2, gp=int(t.get("gasPrice", "0x0"), 16), bn=int(t["blockNumber"], 16), ti=int(t["transactionIndex"], 16))
        if h in early: r["in"] = t["input"]
        rows.append(r)
    fp = os.path.join(HERE, fname(k))
    if os.path.exists(fp) and os.path.getsize(fp) > 1_500_000: k += 1
    jl_append(rows, fname(k))
    print(i + len(ch), rpc.STATS, flush=True)
