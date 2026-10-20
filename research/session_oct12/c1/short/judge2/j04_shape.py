"""Judge 2, step 4 (RPC, read-only, paced ../../rpc.py): the 14:00 UTC launch shape (sqrtP 835109957917073511657837871095390, liquidity
94871533698238694366969). From the analyst's head (86,735,446) to the current head: every C-1-type launch (Initialize fee 100, tick spacing
1, ETH pair, no hook, a 2,276-byte value-0 PositionManager call); for every launch since 13:30 UTC (old and new shape), its Swap and
ModifyLiquidity logs and the transactions behind its swaps (router calldata), so that both shapes can be compared on the same clock.
Writes j04_launches.json, j04_events.jsonl, j04_txs.jsonl (incremental), j04_meta.json."""
from jc import *
import calendar
OLD_HEAD = 86735446; T1330 = calendar.timegm((2026, 10, 12, 13, 30, 0))
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
print(f"head {head} {utc(th)}")
ls = []
for a in range(OLD_HEAD + 1, head + 1, 100000):
    ls += rpc.logs({"address": PM, "topics": [T_INIT]}, a, min(a + 99999, head))
cand = [l for l in ls if W(l["data"], 0) == 100 and W(l["data"], 1) == 1 and l["topics"][2][-40:] == "0" * 40]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
new = []
for l, tx in zip(cand, txs):
    to = (tx.get("to") or "").lower() if tx else ""; n = (len(tx["input"]) - 2) // 2 if tx else 0; v = int(tx["value"], 16) if tx else -1
    new.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": tx["from"].lower() if tx else None,
                "to": to, "n": n, "value": v, "sel": tx["input"][2:10] if tx else None, "sqrtP": W(l["data"], 3), "tick": sgn(W(l["data"], 4)),
                "hooks": "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3], "c1": to == POSM and n == 2276 and v == 0})
bl = sorted(set(x["lb"] for x in new))
blk = {b: int(r["timestamp"], 16) for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl]))} if bl else {}
for x in new: x["ts"] = blk[x["lb"]]
print(f"Initialize logs {len(ls)}; fee 100 / ts 1 / ETH {len(cand)}; 2,276-byte value-0 PositionManager calls {sum(x['c1'] for x in new)}")
old = [dict(x, c1=True) for x in json.load(open(SH("s01_launches_new.json"))) if x["ts"] >= T1330]
allL = old + [x for x in new if x["c1"]]
json.dump(allL, open(JD("j04_launches.json"), "w"))
for x in allL: print(f"   {utc(x['ts'])} {x['pid'][:10]} lb {x['lb']} sqrtP {x['sqrtP']} from {x['from']}")
# events of every launch since 13:30 (Swap and ModifyLiquidity), from its launch to the head
ids = sorted(x["pid"] for x in allL); a0 = min(x["lb"] for x in allL)
ev = []
for a in range(a0, head + 1, 100000):
    ev += rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, min(a + 99999, head))
seen = set(); E = []
for l in ev:
    k = (l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); E.append({k2: l[k2] for k2 in ("blockNumber", "logIndex", "transactionIndex", "transactionHash", "topics", "data")})
E.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
with open(JD("j04_events.jsonl"), "w") as f:
    for l in E: f.write(json.dumps(l) + "\n")
print(f"events {len(E)} (swaps {sum(l['topics'][0] == T_SWAP for l in E)}, ML {sum(l['topics'][0] == T_ML for l in E)})")
# transactions behind the swaps within launch + 1500 and every ML (the router's calldata, the senders)
LB = {x["pid"]: x["lb"] for x in allL}
need = sorted({l["transactionHash"] for l in E if l["topics"][0] == T_ML or int(l["blockNumber"], 16) - LB[l["topics"][1]] <= 1500})
have = {}
for fn in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl"), JD("j04_txs.jsonl")):
    if os.path.exists(fn):
        for l in open(fn): have[json.loads(l)["hash"]] = 1
todo = [h for h in need if h not in have]; print(f"transactions needed {len(need)}, to fetch {len(todo)}", flush=True)
with open(JD("j04_txs.jsonl"), "a") as f:
    for i in range(0, len(todo), 200):
        ch = todo[i:i + 200]
        for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch])):
            if t is None: continue
            to = (t.get("to") or "").lower(); inp = t["input"]
            f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": to, "sel": inp[2:10], "n": (len(inp) - 2) // 2, "value": int(t["value"], 16),
                                "nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "input": inp[:2 + 8 + 64 * 12] if to == ROUTER else inp[:2 + 8 + 64 * 40]}) + "\n")
        f.flush(); print(f"  {min(i + 200, len(todo))}/{len(todo)} rpc {rpc.STATS}", flush=True)
json.dump({"head": head, "head_ts": th, "from": OLD_HEAD + 1}, open(JD("j04_meta.json"), "w"))
print("rpc", rpc.STATS)
