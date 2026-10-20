"""The last 2.4333 pools (launched in the last 2 h 10 min of the line): every Swap to launch + 3,000 blocks and every ModifyLiquidity to the head,
with the transaction (from/to/selector) behind every swap to launch + 600. Cached in s08_pools_cache.jsonl; the table in s08_last_pools.out."""
import json, time, collections
from clusters import load
from common import R, PM, T_SWAP, T_ML, BOT, W, sgn, p, load_jsonl, append_jsonl
DECOY = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
meta = json.load(open(p("s01_meta.json"))); head = meta["head"]
rows = [r for r in load() if r["fam"].startswith("VB 2.4333")]
last_t = rows[-1]["t"]; sel = [r for r in rows if r["t"] >= last_t - 2 * 3600 - 600]
have = {x["pid"] for x in load_jsonl("s08_pools_cache.jsonl")}
for r in sel:
    if r["pid"] in have: continue
    L = r["b"]
    sw = sorted(R.logs({"address": PM, "topics": [T_SWAP, r["pid"]]}, L, min(L + 3000, head)), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    ml = R.logs({"address": PM, "topics": [T_ML, r["pid"]]}, L, head)
    near = [s for s in sw if int(s["blockNumber"], 16) <= L + 600]
    txs = R.batch("eth_getTransactionByHash", [[s["transactionHash"]] for s in near]) if near else []
    tx = {s["transactionHash"]: t for s, t in zip(near, txs)}
    ev = []
    for s in sw:
        t = tx.get(s["transactionHash"]) or {}
        ev.append({"d": int(s["blockNumber"], 16) - L, "a0": sgn(W(s["data"], 0)), "a1": sgn(W(s["data"], 1)), "sp": W(s["data"], 2), "liq": W(s["data"], 3), "snd": "0x" + s["topics"][2][-40:],
                   "from": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[:10], "h": s["transactionHash"]})
    mls = [{"d": int(m["blockNumber"], 16) - L, "lo": sgn(W(m["data"], 0)), "hi": sgn(W(m["data"], 1)), "dl": sgn(W(m["data"], 2)), "snd": "0x" + m["topics"][2][-40:], "h": m["transactionHash"]} for m in ml]
    append_jsonl("s08_pools_cache.jsonl", [{"pid": r["pid"], "L": L, "t": r["t"], "token": r["c1"], "from": r["from"], "swaps": ev, "mls": mls, "head": head}])
    print(time.strftime("%H:%M:%S", time.gmtime(r["t"])), len(sw), len(ml), R.STATS, flush=True)
