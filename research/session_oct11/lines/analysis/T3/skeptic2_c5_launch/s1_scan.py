"""Skeptic 2, candidate 5 (a 1444-byte PositionManager launch, any line, shortly before T).
Stage 1, a slice the finder never saw: every block after the finder's head (precursor/pools.json head 86150647) to the chain head now.
Every Initialize log on the PoolManager in the slice, every launch tx -> the 1444-byte PositionManager launches of any line (the signal),
the 3.0 pools (value 3.0 ETH, fee 10000, spacing 200, no hook, sqrtP 6.79e32), their Swap/ModifyLiquidity logs to L+400 and the txs of
their swaps to L+150 and of every liquidity call -> s1_slice.json. Read-only, public RPC only."""
import sys, json, collections
from lib import *
FINDER_HEAD = 86150647
start = FINDER_HEAD + 1
head = int(rpc("eth_blockNumber", []), 16)
bh = rpc("eth_getBlockByNumber", [hex(head), False]); bs = rpc("eth_getBlockByNumber", [hex(start), False])
ts_h, ts_s = int(bh["timestamp"], 16), int(bs["timestamp"], 16)
print(f"slice {start}..{head}: {utc(ts_s)} -> {utc(ts_h)} UTC, {(head - start) / (ts_h - ts_s):.2f} blocks/s, {(ts_h - ts_s) / 3600:.2f} h", flush=True)
ini = []
for a in range(start, head + 1, 10000):
    ini += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 9999, head))
print("Initialize logs (all pairs):", len(ini), flush=True)
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
itx = gettx([l["transactionHash"] for l in ini])
launches = []          # every Initialize with its launch tx
for l, t in zip(ini, itx):
    d = l["data"]
    rec = {"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
           "pid": l["topics"][1], "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:], "fee": W(d, 0), "ts": sgn(W(d, 1)),
           "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtP": W(d, 3),
           "to": (t or {}).get("to", "") and t["to"].lower(), "from": (t or {}).get("from", "") and t["from"].lower(),
           "clen": (len(t["input"]) - 2) // 2 if t else None, "sel": t["input"][2:10] if t else None, "value": int(t["value"], 16) if t else None}
    rec["is1444"] = rec["to"] == POSM and rec["clen"] == 1444
    rec["line"] = None
    if rec["is1444"]:
        rec["line"] = {3 * 10 ** 18: "3.0", 2433328500000000000: "2.433"}.get(rec["value"], f"v{rec['value'] / 1e18:g}")
        if rec["line"] == "3.0" and not (rec["fee"] == 10000 and rec["ts"] == 200 and rec["sqrtP"] == SQRT30 and int(rec["hooks"], 16) == 0 and int(rec["c0"], 16) == 0):
            rec["line"] = "3.0-othershape"
    launches.append(rec)
print("Initialize by launch kind:", collections.Counter((r["to"] == POSM, r["clen"], r["line"]) for r in launches).most_common(20), flush=True)
pools = [dict(pid=r["pid"], token=r["c1"], L=r["bn"], lti=r["ti"], launch_tx=r["tx"], launcher=r["from"]) for r in launches if r["line"] == "3.0"]
pools.sort(key=lambda p: p["L"])
print("3.0 pools in the slice:", len(pools), flush=True)
ev = collections.defaultdict(list)
for i in range(0, len(pools), 15):
    g = pools[i:i + 15]; a = g[0]["L"]; b = min(g[-1]["L"] + 400, head)
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b): ev[l["topics"][1]].append(l)
    print(f"  pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
    p["span"] = min(400, head - p["L"])
need = [e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 150]
gettx(need)
txs = {h: kv_tx.d[h] for h in set(need) | {r["tx"] for r in launches} if h in kv_tx.d}
json.dump({"start": start, "head": head, "ts_start": ts_s, "ts_head": ts_h, "launches": launches, "pools": pools, "txs": txs}, open("s1_slice.json", "w"))
print("saved s1_slice.json", flush=True)
