"""The token deployments behind the volume bot's launches: every token minted to the bot router (s06, 0x0 -> 0x1cbaf24d) - the transaction
(sender, nonce, value, calldata length, selector) and its receipt (how many Transfers: the supply's fan-out). Cached in s11_deploy_cache.jsonl."""
import json
from common import R, load_jsonl, append_jsonl, T_TRANSFER
mints = [m for m in load_jsonl("s06_bot_transfers_cache.jsonl") if m["side"] == "to" and int(m["t1"], 16) == 0]
have = {x["h"] for x in load_jsonl("s11_deploy_cache.jsonl")}
hs = sorted({m["h"] for m in mints} - have)
print("to fetch", len(hs))
for i in range(0, len(hs), 40):
    ch = hs[i:i + 40]
    txs = R.batch("eth_getTransactionByHash", [[h] for h in ch]); rcs = R.batch("eth_getTransactionReceipt", [[h] for h in ch], n=10)
    rows = []
    for h, tx, rc in zip(ch, txs, rcs):
        tr = [lg for lg in rc["logs"] if lg["topics"][0] == T_TRANSFER]
        rows.append({"h": h, "b": int(tx["blockNumber"], 16), "from": tx["from"].lower(), "to": tx["to"].lower(), "nonce": int(tx["nonce"], 16), "value": str(int(tx["value"], 16)),
                     "clen": (len(tx["input"]) - 2) // 2, "sel": tx["input"][:10], "gas": int(tx["gas"], 16), "gasUsed": int(rc["gasUsed"], 16), "status": int(rc["status"], 16),
                     "ntransfer": len(tr), "token": tr[0]["address"].lower() if tr else None,
                     "recipients": sorted({"0x" + lg["topics"][2][-40:] for lg in tr})[:400], "nlogs": len(rc["logs"])})
    append_jsonl("s11_deploy_cache.jsonl", rows)
    print(i + len(ch), R.STATS, flush=True)
