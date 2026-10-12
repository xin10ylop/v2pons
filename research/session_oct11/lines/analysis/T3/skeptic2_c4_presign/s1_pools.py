"""Stage 1 (skeptic 2, candidate 4): the 3.0 line's launches in the most recent ~2 hours, disjoint from the finder's slice
(the finder's head was block 86158232, 10-11 21:45:04 UTC; we take L > 86158232). Shape: Initialize of an ETH pair, no hook, fee 10000,
spacing 200, sqrtP 679394651928963067279918579724198; launch tx to the PositionManager 0x58daec31, msg.value 3.0 ETH, 1,444-byte input.
Per pool every Swap / ModifyLiquidity log to L+400 (or the head), the transactions of the swaps to L+120 and of every liquidity call.
-> pools.json"""
import sys, json, collections
from lib import *
FROM = int(sys.argv[1]) if len(sys.argv) > 1 else 86158233
head = int(rpc("eth_blockNumber", []), 16); bh = rpc("eth_getBlockByNumber", [hex(head), False]); b0 = rpc("eth_getBlockByNumber", [hex(FROM), False])
print(f"slice: blocks {FROM}..{head} = {utc(int(b0['timestamp'],16))} .. {utc(int(bh['timestamp'],16))} UTC", flush=True)
ini = []
for a in range(FROM, head + 1, 20000):
    ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, head))
cand = [l for l in ini if W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200]
print("ETH-pair Initialize logs", len(ini), "3.0 shape", len(cand), flush=True)
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"   txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
ltx = gettx([l["transactionHash"] for l in cand])
pools = []; rej = collections.Counter()
for l, t in zip(cand, ltx):
    if not t: rej["no tx"] += 1; continue
    if (t.get("to") or "").lower() != POSM: rej["to " + (t.get("to") or "")[:10]] += 1; continue
    if (len(t["input"]) - 2) // 2 != 1444: rej[f"len {(len(t['input'])-2)//2}"] += 1; continue
    if int(t["value"], 16) != 3 * 10 ** 18: rej[f"value {int(t['value'],16)/1e18}"] += 1; continue
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": int(l["blockNumber"], 16), "lti": int(l["transactionIndex"], 16),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
pools.sort(key=lambda p: p["L"])
print("3.0 launches", len(pools), "rejected", dict(rej), flush=True)
ev = collections.defaultdict(list)
for i in range(0, len(pools), 15):
    g = pools[i:i + 15]; a = g[0]["L"]; b = min(g[-1]["L"] + 400, head)
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b):
        ev[l["topics"][1]].append(l)
    print(f"   pool events {i + len(g)}/{len(pools)}", flush=True)
for p in pools:
    es = sorted((l for l in ev[p["pid"]] if int(l["blockNumber"], 16) <= p["L"] + 400), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16),
                "tx": l["transactionHash"], "sender": "0x" + l["topics"][2][-40:], "data": l["data"]} for l in es]
    p["span"] = min(400, head - p["L"])
need = [e["tx"] for p in pools for e in p["ev"] if e["kind"] == "ml" or e["bn"] <= p["L"] + 120]
print("swap/ml txs:", len(set(need)), flush=True)
gettx(need)
json.dump({"head": head, "head_ts": int(bh["timestamp"], 16), "from": FROM, "pools": pools}, open("pools.json", "w"))
print("written pools.json", flush=True)
