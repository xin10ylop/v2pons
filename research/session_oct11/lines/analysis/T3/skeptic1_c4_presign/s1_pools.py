"""Stage 1 (per slice): every 3.0 launch in [a, b]: PoolManager Initialize with currency0 = ETH, fee 10000, spacing 200, no hook, sqrtP = SQRT30;
launch tx to the PositionManager, value exactly 3.0 ETH, 1,444-byte input. Then each pool's Swap/ModifyLiquidity logs L..L+200 and the txs of
every swap to L+100 and every liquidity call. -> pools_<slice>.json.  usage: s1_pools.py <slice> <from_block> <to_block>"""
import sys, json, collections, os
from lib import *
name, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
head = int(rpc("eth_blockNumber", []), 16)
fn = f"init_{name}.json"
if os.path.exists(fn): ini = json.load(open(fn))
else:
    ini = []
    for x in range(a, b + 1, 20000):
        ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, x, min(x + 19999, b))
    json.dump(ini, open(fn, "w"))
ta = int(rpc("eth_getBlockByNumber", [hex(a), False])["timestamp"], 16); tb = int(rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
cand = [l for l in ini if W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30]
print(f"slice {name}: blocks {a}..{b} = {utc(ta)} .. {utc(tb)} UTC; ETH-pair Initialize logs {len(ini)}; 3.0 shape {len(cand)}", flush=True)
kv_tx = KV("tx")
ltx = gettx([l["transactionHash"] for l in cand], kv_tx)
pools, rej = [], collections.Counter()
for l, t in zip(cand, ltx):
    if not t: rej["no tx"] += 1; continue
    ok = (t.get("to") or "").lower() == POSM and int(t["value"], 16) == 3 * 10 ** 18 and (len(t["input"]) - 2) // 2 == 1444
    if not ok: rej[((t.get("to") or "")[:10], int(t["value"], 16) / 1e18, (len(t["input"]) - 2) // 2)] += 1; continue
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
pools.sort(key=lambda p: p["L"])
print(f"3.0 launches {len(pools)}; rejected {dict(rej)}", flush=True)
ev = collections.defaultdict(list)
for i in range(0, len(pools), 20):
    g = pools[i:i + 20]; x = g[0]["L"]; y = min(g[-1]["L"] + 200, head)
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, x, y): ev[l["topics"][1]].append(l)
    print(f"   pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 200), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
need = [e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 100]
print("swap/ml txs:", len(set(need)), flush=True)
gettx(need, kv_tx)
json.dump({"slice": name, "a": a, "b": b, "ta": ta, "tb": tb, "pools": pools}, open(f"pools_{name}.json", "w"))
