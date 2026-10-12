"""All PoolManager Initialize events from block A to head; decode; fetch launch txs."""
import kc, json, sys
A = 85800000
head = int(kc.R.call("eth_blockNumber", []), 16)
lg = kc.cached_logs("k01_inits_cache.jsonl", {"address": kc.PM, "topics": [kc.T_INIT]}, A, head, step=50000)
rows = []
for l in lg:
    d = l["data"]; t = l["topics"]
    rows.append({"block": int(l["blockNumber"], 16), "tx": l["transactionHash"], "id": t[1], "c0": kc.topaddr(t[2]), "c1": kc.topaddr(t[3]),
                 "fee": kc.W(d, 0), "ts": kc.sgn(kc.W(d, 1)), "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtp": kc.W(d, 3), "tick": kc.sgn(kc.W(d, 4))})
print("inits", len(rows), "head", head)
tx = kc.txs("k01_tx_cache.jsonl", [r["tx"] for r in rows])
bt = kc.block_ts_map("k01_bt_cache.jsonl", [r["block"] for r in rows])
for r in rows:
    x = tx.get(r["tx"], {})
    r.update({"t": bt[r["block"]], "from": x.get("from"), "to": x.get("to"), "value": x.get("value"), "clen": (len(x.get("input", "0x")) - 2) // 2, "sel": x.get("input", "")[:10], "nonce": x.get("nonce"), "gas": x.get("gas")})
json.dump({"head": head, "rows": rows}, open(kc.p("k01_inits_cache.json"), "w"))
