"""Stage 1 (skeptic 2, candidate 3 'precursor events'): every 3.0 launch of the volume bot in the last N hours, re-read from the public RPC
(own caches, not the finder's): Initialize (ETH pair, no hook, fee 10000, spacing 200, sqrtP 6.79e32) whose launch tx goes to the
PositionManager with exactly 3.0 ETH and 1,444 bytes; each pool's Swap/ModifyLiquidity logs to L+400 (or the head) and the transaction of every
one of them -> u6_pools.json. Re-runnable: launches already read are kept, only new blocks are scanned.
Usage: python3 u6a_pools_long.py HOURS (a copy of u1_pools.py writing u6_*.json: the longer window for the reaction lags)"""
import sys, json, collections, os
from lib import *
os.chdir(HERE)
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 7
head = int(rpc("eth_blockNumber", []), 16)
bh = rpc("eth_getBlockByNumber", [hex(head), False]); b0 = rpc("eth_getBlockByNumber", [hex(head - 20000), False])
bps = 20000 / (int(bh["timestamp"], 16) - int(b0["timestamp"], 16)); start = head - int(hours * 3600 * bps)
print(f"head {head} {utc(int(bh['timestamp'], 16))} UTC, {bps:.2f} blocks/s, launches from block {start}", flush=True)
old = json.load(open("u6_init.json")) if os.path.exists("u6_init.json") else {"from": start, "to": start - 1, "ini": []}
ini = [l for l in old["ini"] if int(l["blockNumber"], 16) >= start]
a0 = max(start, old["to"] + 1) if old["from"] <= start else start
if old["from"] > start: ini = []
for a in range(a0, head + 1, 20000):
    ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, head))
json.dump({"from": start, "to": head, "ini": ini}, open("u6_init.json", "w"))
cand = [l for l in ini if W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200]
print("Initialize ETH-pair logs", len(ini), "| no hook, fee 10000, spacing 200, the 3.0 price:", len(cand), flush=True)
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]
        for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch], 20)):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
pools = []; skipped = collections.Counter()
for l, t in zip(cand, gettx([l["transactionHash"] for l in cand])):
    if not t or (t.get("to") or "").lower() != POSM or int(t["value"], 16) != 3 * 10 ** 18 or (len(t["input"]) - 2) // 2 != 1444:
        skipped[((t or {}).get("to"), int((t or {}).get("value") or "0x0", 16) / 1e18, (len((t or {}).get("input") or "0x") - 2) // 2)] += 1; continue
    pools.append({"pid": l["topics"][1].lower(), "token": ("0x" + l["topics"][3][-40:]).lower(), "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
pools.sort(key=lambda p: p["L"]); print("3.0 launches:", len(pools), "| same price, not the line's launch tx:", dict(skipped), flush=True)
ev = collections.defaultdict(list)
for i in range(0, len(pools), 20):
    g = pools[i:i + 20]
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, g[0]["L"], min(g[-1]["L"] + 400, head)):
        ev[l["topics"][1].lower()].append(l)
    print(f"  pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
    p["span"] = min(400, head - p["L"])
gettx([e["tx"] for p in pools for e in p["ev"]])
json.dump({"head": head, "head_ts": int(bh["timestamp"], 16), "bps": bps, "start": start, "pools": pools}, open("u6_pools.json", "w"))
print("saved u6_pools.json", flush=True)
