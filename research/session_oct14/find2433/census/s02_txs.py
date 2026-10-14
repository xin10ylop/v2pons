"""Step 2: transaction + compact receipt for every launch tx of s01 (v4 Initialize and V3 PoolCreated). Resumable.
Receipt kept compact: status, gasUsed, idx, number of logs, and only the logs of PM (ModifyLiquidity/Swap), V3 pools (Initialize/Mint/Swap),
NFT mints (Transfer from 0) of POSM / NPM3, and token mints (Transfer from 0) of any contract. Output s02_tx_cache.jsonl."""
from common import *
hs = []
for f in ("s01_v4init_cache.jsonl", "s01_v3pc_cache.jsonl"):
    hs += [r["h"] for r in jl_load(f)]
have = {r["h"] for r in jl_load("s02_tx_cache.jsonl")}
hs = sorted(set(hs) - have)
print("to fetch", len(hs), "have", len(have), flush=True)
KEEP = {T_ML, T_SWAP, T_V3INIT, T_V3MINT, T_V3SWAP}
for i in range(0, len(hs), 100):
    ch = hs[i:i + 100]
    txs = rpc.batch("eth_getTransactionByHash", [[h] for h in ch], n=25)
    rcs = rpc.batch("eth_getTransactionReceipt", [[h] for h in ch], n=20)
    rows = []
    for h, tx, rc in zip(ch, txs, rcs):
        if not tx or not rc: rows.append({"h": h, "miss": 1}); continue
        lg = []
        for x in rc["logs"]:
            t0 = x["topics"][0] if x["topics"] else ""
            if t0 in KEEP or (t0 == T_TRANSFER and len(x["topics"]) >= 3 and int(x["topics"][1], 16) == 0):
                lg.append({"a": x["address"].lower(), "t": x["topics"], "d": x["data"], "i": int(x["logIndex"], 16)})
        rows.append({"h": h, "b": int(tx["blockNumber"], 16), "from": tx["from"].lower(), "to": (tx.get("to") or "").lower(), "v": str(int(tx["value"], 16)),
                     "in": tx["input"], "n": int(tx["nonce"], 16), "gas": int(tx["gas"], 16), "gp": int(tx.get("gasPrice", "0x0"), 16),
                     "type": int(tx.get("type", "0x0"), 16), "mpf": int(tx.get("maxPriorityFeePerGas", "0x0") or "0x0", 16),
                     "st": int(rc["status"], 16), "gu": int(rc["gasUsed"], 16), "idx": int(rc["transactionIndex"], 16), "nl": len(rc["logs"]),
                     "ca": (rc.get("contractAddress") or ""), "logs": lg})
    jl_append(rows, "s02_tx_cache.jsonl")
    print(i + len(ch), "/", len(hs), rpc.STATS, flush=True)
