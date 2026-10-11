"""Stage 1: every 3.0 launch of the volume bot in the last N hours (Initialize ETH pair, fee 10000, spacing 200, no hook, sqrtP 6.79e32; the
launch tx to the PositionManager, value 3.0 ETH, 1,444 bytes), the pool's Swap/ModifyLiquidity logs to L+400, their transactions -> pools.json.
The 2.4333 line's launches (same PositionManager multicall, value 2.4333 ETH) are kept too, for the bot wallets' history and the cross-pool schedule."""
import sys, json, collections
from lib import *
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 12
head = int(rpc("eth_blockNumber", []), 16)
bh = rpc("eth_getBlockByNumber", [hex(head), False]); b0 = rpc("eth_getBlockByNumber", [hex(head - 20000), False])
bps = 20000 / (int(bh["timestamp"], 16) - int(b0["timestamp"], 16))
start = head - int(hours * 3600 * bps)
print(f"head {head} {utc(int(bh['timestamp'],16))} UTC, {bps:.2f} blocks/s, window from {start}", flush=True)
ini = []
for a in range(start, head + 1, 20000):
    ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, head))
cand = [l for l in ini if W(l["data"], 2) == 0]
print("Initialize ETH-pair logs:", len(ini), "without hook:", len(cand), flush=True)
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    res = batch([("eth_getTransactionByHash", [h]) for h in need])
    for h, t in zip(need, res):
        if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
    kv_tx.flush()
    return [kv_tx.d.get(h) for h in hashes]
ltx = gettx([l["transactionHash"] for l in cand])
pools = []
for l, t in zip(cand, ltx):
    if not (t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444): continue
    v = int(t["value"], 16); line = {3 * 10 ** 18: "3.0", 2433328500000000000: "2.433"}.get(v)
    if line is None: print("  1444-byte PositionManager launch with value", v / 1e18); continue
    if line == "3.0" and not (W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 3) == SQRT30):
        print("  3.0 launch with other shape", W(l["data"], 0), sgn(W(l["data"], 1)), W(l["data"], 3)); continue
    pools.append({"line": line, "fee": W(l["data"], 0), "sqrtP": W(l["data"], 3), "pid": l["topics"][1], "token": "0x" + l["topics"][2][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
print("launches:", collections.Counter(p["line"] for p in pools), flush=True)
# swaps + liquidity per pool, groups of pools close in time
pools.sort(key=lambda p: p["L"])
ev = collections.defaultdict(list)
for i in range(0, len(pools), 20):
    g = pools[i:i + 20]; a = g[0]["L"]; b = min(g[-1]["L"] + 400, head)
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b):
        ev[l["topics"][1]].append(l)
    print(f"  events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
    p["span"] = min(400, head - p["L"])
# transactions of the first 40 swaps and every ML of each pool
need = [e["tx"] for p in pools for e in ([x for x in p["ev"] if x["kind"] == "swap"][:40] + [x for x in p["ev"] if x["kind"] == "ml"])]
print("swap/ml txs to fetch:", len(set(need)) - len(set(need) & set(kv_tx.d)), flush=True)
gettx(need)
json.dump({"head": head, "head_ts": int(bh["timestamp"], 16), "bps": bps, "start": start, "pools": pools}, open("pools.json", "w"))
