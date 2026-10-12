"""Extend the C1R caches (c01/c02/c03, which end at Oct 12 ~13:00 UTC) to the current head, read-only, on the public RPC through the
paced ../rpc.py: new C-1 launches (Initialize on the PoolManager, fee 100, tick spacing 1, ETH pair, a 2,276-byte value-0 PositionManager
call, exactly as c01), every Swap and ModifyLiquidity of the old and new C-1 pools after the old caches' head, our relay's swaps, and the
transactions behind the swaps in [launch, min(pull, launch + 3000)] and [pull - 300, pull] plus every pull (as c03).
Writes s01_meta.json, s01_launches_new.json, s01_events_new.jsonl, s01_relay_new.json, s01_txs_new.jsonl (incremental)."""
from sc import *
OLD = json.load(open(J("c01_launches.json"))); M0 = json.load(open(J("c01_meta.json"))); H0 = json.load(open(J("c02_head.json")))["head"]
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
print(f"old caches: launches to {M0['head']}, events to {H0}; head now {head} {utc(th)}")
# 1. new launches (as c01)
ls = []
for a in range(M0["head"] + 1, head + 1, 100000):
    ls += rpc.logs({"address": PM, "topics": [T_INIT]}, a, min(a + 99999, head))
cand = [l for l in ls if W(l["data"], 0) == 100 and W(l["data"], 1) == 1 and l["topics"][2][-40:] == "0" * 40]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
new = []
for l, tx in zip(cand, txs):
    to = (tx.get("to") or "").lower() if tx else ""; n = (len(tx["input"]) - 2) // 2 if tx else 0; v = int(tx["value"], 16) if tx else -1
    if not (to == POSM and n == 2276 and v == 0): continue
    new.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": tx["from"].lower(),
                "sqrtP": W(l["data"], 3), "tick": sgn(W(l["data"], 4)), "hooks": "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3]})
bl = sorted(set(x["lb"] for x in new))
blk = {b: int(r["timestamp"], 16) for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl]))} if bl else {}
for x in new: x["ts"] = blk[x["lb"]]
oldids = {x["pid"] for x in OLD}; new = [x for x in new if x["pid"] not in oldids]
print(f"Initialize logs {len(ls)}, fee 100 / ts 1 / ETH {len(cand)}, new C-1 launches {len(new)}; sqrtP == SQRTP {sum(x['sqrtP'] == SQRTP for x in new)}; hooks {set(x['hooks'] for x in new)}")
json.dump(new, open(S("s01_launches_new.json"), "w"))
# 2. events (as c02): old pools after the old events head, new pools from their launch
out = []
def grab(ids, a0):
    r = []
    for g in range(0, len(ids), 100):
        for a in range(a0, head + 1, 100000):
            r += rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], ids[g:g + 100]]}, a, min(a + 99999, head))
    return r
out += grab(sorted(oldids), H0 + 1)
if new: out += grab(sorted(x["pid"] for x in new), min(x["lb"] for x in new))
seen = set(); ev = []
for l in out:
    k = (l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); ev.append(l)
ev.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
with open(S("s01_events_new.jsonl"), "w") as f:
    for l in ev: f.write(json.dumps({k: l[k] for k in ("blockNumber", "logIndex", "transactionIndex", "transactionHash", "topics", "data")}) + "\n")
rel = []
for a in range(H0 + 1, head + 1, 100000):
    rel += rpc.logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY[2:]]}, a, min(a + 99999, head))
json.dump(rel, open(S("s01_relay_new.json"), "w"))
print(f"new events {len(ev)} (swaps {sum(l['topics'][0] == T_SWAP for l in ev)}, ML {sum(l['topics'][0] == T_ML for l in ev)}); relay swaps after {H0}: {len(rel)}")
json.dump({"head": head, "head_ts": th, "old_launch_head": M0["head"], "old_event_head": H0, "start": M0["start"], "start_ts": M0["start_ts"]}, open(S("s01_meta.json"), "w"))
# 3. transactions (as c03, CAP 3000), over the merged events
CAP = 3000
X = {x["pid"]: x for x in OLD + new}
allev = jl(J("c02_events.jsonl")) + ev
pull = {}
for l in allev:
    if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0:
        pid = l["topics"][1]; b = int(l["blockNumber"], 16) - X[pid]["lb"]; pull[pid] = min(pull.get(pid, 1 << 60), b)
need = set()
for l in allev:
    pid = l["topics"][1]; b = int(l["blockNumber"], 16) - X[pid]["lb"]; p = pull.get(pid, 1 << 60)
    if l["topics"][0] == T_ML or b <= min(p, CAP) or p - 300 <= b <= p: need.add(l["transactionHash"])
for l in rel: need.add(l["transactionHash"])
have = set()
for fn in (J("c03_txs.jsonl"), S("s01_txs_new.jsonl")):
    if os.path.exists(fn):
        for l in open(fn): have.add(json.loads(l)["hash"])
todo = sorted(need - have); print(f"transactions needed {len(need)}, cached {len(need & have)}, to fetch {len(todo)}", flush=True)
with open(S("s01_txs_new.jsonl"), "a") as f:
    for i in range(0, len(todo), 400):
        ch = todo[i:i + 400]
        for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch])):
            if t is None: print("missing", h); continue
            to = (t.get("to") or "").lower(); inp = t["input"]
            f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": to, "sel": inp[2:10], "n": (len(inp) - 2) // 2, "value": int(t["value"], 16),
                                "nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "gp": int(t.get("gasPrice") or "0x0", 16),
                                "input": inp[:2 + 8 + 64 * 12] if to == ROUTER else inp}) + "\n")
        f.flush(); print(f"  {min(i + 400, len(todo))}/{len(todo)} rpc {rpc.STATS}", flush=True)
print("rpc", rpc.STATS)
