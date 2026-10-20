"""Judge 1, fetch: C-1 launches after the analyst's head (86,735,446, Oct 12 14:14 UTC) to now, both launch shapes (the line's sqrtP and the
14:00 shape: sqrtP 835109957917073511657837871095390, L 94871533698238694366969), plus the two 14:00-shape launches already in s01; their Swap and
ModifyLiquidity logs from the launch to the head; the transactions behind the swaps in [launch, min(pull, launch + 1500)] and every
ModifyLiquidity; the launch transactions' full calldata (old and new shape, to compare). Read-only, public RPC through the paced ../../rpc.py.
Writes j00_launches.json, j00_events.jsonl, j00_txs.jsonl, j00_meta.json."""
from jc import *
S01 = json.load(open(SH("s01_meta.json"))); A = S01["head"] + 1
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
print(f"from {A} to head {head} {utc(th)}")
ls = []
for a in range(A, head + 1, 100000):
    ls += rpc.logs({"address": PM, "topics": [T_INIT]}, a, min(a + 99999, head))
cand = [l for l in ls if W(l["data"], 0) == 100 and W(l["data"], 1) == 1 and l["topics"][2][-40:] == "0" * 40]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
new = []
for l, tx in zip(cand, txs):
    to = (tx.get("to") or "").lower() if tx else ""; n = (len(tx["input"]) - 2) // 2 if tx else 0; v = int(tx["value"], 16) if tx else -1
    if not (to == POSM and n == 2276 and v == 0): continue
    new.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": tx["from"].lower(),
                "sqrtP": W(l["data"], 3), "tick": sgn(W(l["data"], 4)), "hooks": "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3], "input": tx["input"]})
old_new_shape = [x for x in json.load(open(SH("s01_launches_new.json"))) if x["sqrtP"] != SQRTP]
for x in old_new_shape:
    t = rpc.call("eth_getTransactionByHash", [x["tx"]]); x = dict(x, input=t["input"]); new.append(x)
# one old-shape launch's calldata for the comparison
X0 = json.load(open(SH("s01_launches_new.json"))); ref = next(x for x in X0 if x["sqrtP"] == SQRTP)
ref = dict(ref, input=rpc.call("eth_getTransactionByHash", [ref["tx"]])["input"], ref=True)
bl = sorted(set(x["lb"] for x in new))
blk = {b: int(r["timestamp"], 16) for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl]))} if bl else {}
for x in new: x["ts"] = blk[x["lb"]]
new.sort(key=lambda x: x["lb"])
print(f"Initialize {len(ls)}, fee 100/ts 1/ETH {len(cand)}, C-1-call launches {len(new)} (incl. {len(old_new_shape)} 14:00-shape ones from s01)")
for x in new: print(f"  {utc(x['ts'])} {x['pid'][:10]} lb {x['lb']} from {x['from'][:10]} sqrtP {x['sqrtP']}")
json.dump({"launches": new, "ref": ref}, open(JD("j00_launches.json"), "w"))
ids = sorted(x["pid"] for x in new); a0 = min(x["lb"] for x in new)
ev = []
for g in range(0, len(ids), 100):
    for a in range(a0, head + 1, 100000):
        ev += rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], ids[g:g + 100]]}, a, min(a + 99999, head))
seen = set(); E = []
for l in ev:
    k = (l["transactionHash"], l["logIndex"])
    if k not in seen: seen.add(k); E.append(l)
E.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
with open(JD("j00_events.jsonl"), "w") as f:
    for l in E: f.write(json.dumps({k: l[k] for k in ("blockNumber", "logIndex", "transactionIndex", "transactionHash", "topics", "data")}) + "\n")
print(f"events {len(E)} (swaps {sum(l['topics'][0] == T_SWAP for l in E)}, ML {sum(l['topics'][0] == T_ML for l in E)})")
X = {x["pid"]: x for x in new}; pull = {}
for l in E:
    if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0:
        pid = l["topics"][1]; pull[pid] = min(pull.get(pid, 1 << 60), int(l["blockNumber"], 16) - X[pid]["lb"])
need = set()
for l in E:
    pid = l["topics"][1]; b = int(l["blockNumber"], 16) - X[pid]["lb"]
    if l["topics"][0] == T_ML or b <= min(pull.get(pid, 1 << 60), 1500): need.add(l["transactionHash"])
todo = sorted(need); print(f"transactions to fetch {len(todo)}", flush=True)
with open(JD("j00_txs.jsonl"), "w") as f:
    for i in range(0, len(todo), 400):
        ch = todo[i:i + 400]
        for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch])):
            if t is None: print("missing", h); continue
            to = (t.get("to") or "").lower(); inp = t["input"]
            f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": to, "sel": inp[2:10], "n": (len(inp) - 2) // 2, "value": int(t["value"], 16),
                                "nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "input": inp[:2 + 8 + 64 * 12] if to == ROUTER else inp[:2 + 8 + 64 * 40]}) + "\n")
        f.flush(); print(f"  {min(i + 400, len(todo))}/{len(todo)} rpc {rpc.STATS}", flush=True)
json.dump({"head": head, "head_ts": th, "from": A}, open(JD("j00_meta.json"), "w"))
print("rpc", rpc.STATS)
