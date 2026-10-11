"""Skeptic 1, candidate 2 (bot-wallet precursor). Stage 1: every 3.0 launch of the volume bot in an OLD slice the finder did not use
(blocks 85,452,462..85,734,702 = 10-11 01:27..09:38 UTC; the finder's pools start at 85,734,703). Launch = Initialize on the v4 PoolManager,
ETH pair (currency0 = 0), fee 10000, spacing 200, no hook, sqrtP 679394651928963067279918579724198, from a 1,444-byte tx to the PositionManager
0x58daec31 with value exactly 3.0 ETH. Per pool: Swap/ModifyLiquidity logs to L+200 and the transactions of every swap to L+120 and every
liquidity call -> pools.json. Public RPC only, read-only."""
import sys, json, os, collections
from lib import *
A, B = 85452462, 85734702
kv_tx = KV("tx")
if os.path.exists("init_logs.json"): ini = json.load(open("init_logs.json"))
else:
    ini = []
    for a in range(A, B + 1, 20000):
        ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, B))
    json.dump(ini, open("init_logs.json", "w"))
cand = [l for l in ini if W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30]
print(f"slice {A}..{B}; ETH-pair Initialize logs {len(ini)}; fee 10000 / spacing 200 / no hook / 3.0 price: {len(cand)}", flush=True)
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
ltx = gettx([l["transactionHash"] for l in cand])
pools = []; rej = collections.Counter()
for l, t in zip(cand, ltx):
    if not t: rej["no tx"] += 1; continue
    if (t.get("to") or "").lower() != POSM: rej["not POSM"] += 1; continue
    if (len(t["input"]) - 2) // 2 != 1444: rej[f"len {(len(t['input']) - 2) // 2}"] += 1; continue
    if int(t["value"], 16) != 3 * 10 ** 18: rej[f"value {int(t['value'], 16) / 1e18}"] += 1; continue
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
print("3.0 launches:", len(pools), "rejected:", dict(rej), flush=True)
pools.sort(key=lambda p: p["L"])
ev = collections.defaultdict(list)
for i in range(0, len(pools), 15):
    g = pools[i:i + 15]; a = g[0]["L"]; b = g[-1]["L"] + 200
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b): ev[l["topics"][1]].append(l)
    if (i // 15) % 5 == 0: print(f"  pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 200), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "data": l["data"]} for l in es]
need = [e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 120]
print("swap/ml txs:", len(set(need)), flush=True)
gettx(need)
json.dump({"A": A, "B": B, "pools": pools}, open("pools.json", "w"))
print("done", flush=True)
