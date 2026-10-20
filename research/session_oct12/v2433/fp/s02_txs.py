"""The transaction and receipt behind every Initialize log of s01 (cached in s02_tx_cache.jsonl, resumable)."""
import json
from common import R, p, load_jsonl, append_jsonl
inits = load_jsonl("s01_inits_cache.jsonl")
have = {r["h"] for r in load_jsonl("s02_tx_cache.jsonl")}
hs = sorted({l["transactionHash"] for l in inits} - have)
print("to fetch", len(hs), "have", len(have))
for i in range(0, len(hs), 100):
    ch = hs[i:i + 100]
    txs = R.batch("eth_getTransactionByHash", [[h] for h in ch])
    rcs = R.batch("eth_getTransactionReceipt", [[h] for h in ch])
    rows = []
    for h, tx, rc in zip(ch, txs, rcs):
        if not tx or not rc: continue
        rows.append({"h": h, "b": int(tx["blockNumber"], 16), "from": tx["from"].lower(), "to": (tx.get("to") or "").lower(), "value": int(tx["value"], 16),
                     "input": tx["input"], "nonce": int(tx["nonce"], 16), "gas": int(tx["gas"], 16), "gp": int(tx.get("gasPrice", "0x0"), 16),
                     "status": int(rc["status"], 16), "gasUsed": int(rc["gasUsed"], 16), "idx": int(rc["transactionIndex"], 16),
                     "logs": [{"a": lg["address"].lower(), "t": lg["topics"], "d": lg["data"], "i": int(lg["logIndex"], 16)} for lg in rc["logs"]]})
    append_jsonl("s02_tx_cache.jsonl", rows)
    print(i + len(ch), "/", len(hs), R.STATS, flush=True)
