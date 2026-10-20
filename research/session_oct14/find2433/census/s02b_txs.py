"""Step 2b: the transaction (no receipt) behind every launch tx of s01 not yet in s02_tx_cache.jsonl (receipts proved too slow on the shared
public RPC; liquidity and pulls come from per-pool ModifyLiquidity logs in s05). Output s02_tx_cache.jsonl (same row format, no logs)."""
from common import *
hs = []
for f in ("s01_v4init_cache.jsonl", "s01_v3pc_cache.jsonl"):
    hs += [r["h"] for r in jl_load(f)]
have = {r["h"] for r in jl_load("s02_tx_cache.jsonl") if "miss" not in r}
hs = set(hs) - have
# fetch the launches that log fields cannot already place first: tokens minted to the bot router (VB 3.0/5.0) and the S1/S2 hooks go last
botmint = {r["tok"] for r in jl_load("s03_botmints_cache.jsonl") if "tok" in r}
late = set()
for l in jl_load("s01_v4init_cache.jsonl"):
    hk = l["d"][2 + 64 * 2 + 24: 2 + 64 * 3]
    if "0x" + l["t"][3][-40:] in botmint or hk.startswith("4e346895") or hk.startswith("2c668601"): late.add(l["h"])
hs = sorted(hs, key=lambda h: (h in late, h))
print("late (known from logs)", len(late & set(hs)), flush=True)
print("to fetch", len(hs), "have", len(have), flush=True)
for i in range(0, len(hs), 200):
    ch = hs[i:i + 200]
    txs = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    rows = []
    for h, tx in zip(ch, txs):
        if not tx: rows.append({"h": h, "miss": 1}); continue
        rows.append({"h": h, "b": int(tx["blockNumber"], 16), "from": tx["from"].lower(), "to": (tx.get("to") or "").lower(), "v": str(int(tx["value"], 16)),
                     "in": tx["input"], "n": int(tx["nonce"], 16), "gas": int(tx["gas"], 16), "gp": int(tx.get("gasPrice", "0x0"), 16),
                     "type": int(tx.get("type", "0x0"), 16), "mpf": int(tx.get("maxPriorityFeePerGas", "0x0") or "0x0", 16), "idx": int(tx["transactionIndex"], 16)})
    jl_append(rows, "s02_tx_cache.jsonl")
    print(i + len(ch), "/", len(hs), rpc.STATS, flush=True)
