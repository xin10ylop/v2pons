"""Stage 1 (skeptic 2, candidate 6): re-read from the public RPC (no other cache) every Initialize on the PoolManager in the last HOURS
(ETH pair), the 3.0 launches among them (no hook, fee 10000, spacing 200, sqrtP 6.79e32, launch tx to the PositionManager with 3.0 ETH and
1,444 bytes), each 3.0 pool's Swap/ModifyLiquidity logs to L+400 (or the head) with the transaction of every swap to L+120 and every
liquidity call; and every Swap/ModifyLiquidity the bot router 0x1cbaf24d executed anywhere in the window (topic2 = the router).
Usage: python3 s1_pools.py HOURS  -> s1_pools.json"""
import sys, json, collections, os
from lib import *
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2.6
os.chdir(HERE)
head = int(rpc("eth_blockNumber", []), 16)
bh = rpc("eth_getBlockByNumber", [hex(head), False]); b0 = rpc("eth_getBlockByNumber", [hex(head - 20000), False])
bps = 20000 / (int(bh["timestamp"], 16) - int(b0["timestamp"], 16)); start = head - int(hours * 3600 * bps)
print(f"head {head} {utc(int(bh['timestamp'], 16))} UTC, {bps:.2f} blocks/s, window from block {start}", flush=True)
ini = []
for a in range(start, head + 1, 20000):
    ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, head))
print("Initialize ETH-pair logs:", len(ini), flush=True)
prices = collections.Counter(W(l["data"], 3) for l in ini if W(l["data"], 2) == 0)
print("most common launch prices (no hook):", prices.most_common(6), flush=True)
cand = [l for l in ini if W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200]
print("no hook, fee 10000, spacing 200, the 3.0 price:", len(cand), flush=True)
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]
        for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch], 20)):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
pools = []
for l, t in zip(cand, gettx([l["transactionHash"] for l in cand])):
    if not t or (t.get("to") or "").lower() != POSM or int(t["value"], 16) != 3 * 10 ** 18 or (len(t["input"]) - 2) // 2 != 1444:
        print("  skipped (not the line's launch tx):", l["transactionHash"][:12], (t or {}).get("to"), int((t or {}).get("value") or "0x0", 16) / 1e18); continue
    pools.append({"pid": l["topics"][1].lower(), "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
pools.sort(key=lambda p: p["L"]); print("3.0 launches:", len(pools), flush=True)
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
gettx([e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 120])
# every swap / liquidity call the bot router executed in the window (any pool)
botev = []
for a in range(start, head + 1, 20000):
    botev += logs({"address": PM, "topics": [[T_SWAP, T_ML], None, "0x" + "0" * 24 + BOT[2:]]}, a, min(a + 19999, head))
botev = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "pid": l["topics"][1].lower(), "bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16),
          "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "data": l["data"]} for l in botev]
print("bot-router events in the window:", collections.Counter(e["kind"] for e in botev), "pools:", len(set(e["pid"] for e in botev)), flush=True)
json.dump({"head": head, "head_ts": int(bh["timestamp"], 16), "bps": bps, "start": start, "pools": pools,
           "inits": [{"pid": l["topics"][1].lower(), "bn": int(l["blockNumber"], 16), "fee": W(l["data"], 0), "ts": sgn(W(l["data"], 1)), "hook": W(l["data"], 2),
                      "sp": W(l["data"], 3), "tok": "0x" + l["topics"][3][-40:]} for l in ini], "botev": botev}, open("s1_pools.json", "w"))
print("saved s1_pools.json", flush=True)
