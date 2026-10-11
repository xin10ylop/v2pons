"""Skeptic 1, stage 1: every 3.0 launch of the volume bot in the OLDEST slice the finder did not use: blocks [A, B) with B = 85,734,703
(the precursor angle's first block, 10-11 09:38:24 UTC) and A = 8 hours earlier (~01:38 UTC). Launch = Initialize (ETH pair, fee 10000,
tick spacing 200, no hook, sqrtP 679394651928963067279918579724198), launch tx to the PositionManager, value 3.0 ETH, 1,444 bytes.
Then each pool's Swap/ModifyLiquidity logs to L+250 and the transactions of every swap to L+150 and every liquidity call -> pools.json."""
import sys, json, collections, os
from lib import *
B = 85734703; A = B - int(8 * 3600 * 9.585); TAG = ""
if len(sys.argv) > 2: A, B, TAG = int(sys.argv[1]), int(sys.argv[2]), "_" + sys.argv[3]   # a second slice: the newest pools after the finder's last (L > 86150251)
SQRT30 = 679394651928963067279918579724198
head = int(rpc("eth_blockNumber", []), 16)
if os.path.exists(f"init_logs{TAG}.json"): ini = json.load(open(f"init_logs{TAG}.json"))
else:
    ini = []
    for a in range(A, B, 20000):
        ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, B - 1))
        print("  init logs to", min(a + 19999, B - 1), len(ini), flush=True)
    json.dump(ini, open(f"init_logs{TAG}.json", "w"))
tsA = int(rpc("eth_getBlockByNumber", [hex(A), False])["timestamp"], 16); tsB = int(rpc("eth_getBlockByNumber", [hex(B), False])["timestamp"], 16)
print(f"slice blocks {A}..{B-1}  {utc(tsA)} .. {utc(tsB)} UTC; ETH-pair Initialize logs {len(ini)}")
cand = [l for l in ini if W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30]
print("fee 10000 / spacing 200 / no hook / the 3.0 price:", len(cand))
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
ltx = gettx([l["transactionHash"] for l in cand])
pools = []; other = collections.Counter()
for l, t in zip(cand, ltx):
    ok = t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and int(t["value"], 16) == 3 * 10 ** 18
    if not ok:
        other[((t or {}).get("to") or "")[:10] + " v=" + str(int(t["value"], 16) / 1e18 if t else None) + " len=" + str((len(t["input"]) - 2) // 2 if t else None)] += 1; continue
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
print("3.0 launches:", len(pools), "; same price/fee but not the line's launch tx:", dict(other))
pools.sort(key=lambda p: p["L"])
ev = collections.defaultdict(list)
for i in range(0, len(pools), 15):
    g = pools[i:i + 15]; a = g[0]["L"]; b = g[-1]["L"] + 250
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b):
        ev[l["topics"][1]].append(l)
    print(f"  pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 250), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
need = [e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 150]
print("swap/ml txs:", len(set(need)), flush=True)
gettx(need)
json.dump({"A": A, "B": B, "tsA": tsA, "tsB": tsB, "pools": pools}, open(f"pools{TAG}.json", "w"))
print("done")
