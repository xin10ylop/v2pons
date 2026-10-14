"""Step 5: per-pool events for the target pools listed in s05_targets.json (pool ids chosen by s04b).
v4: Swap logs [L, L+SW] and ModifyLiquidity logs [L, head] on the PoolManager, pool id as topic 1 (one value per position: no range limit).
V3: Swap/Mint/Burn/Initialize logs on the pool address [L, head] (Swap kept only to L+SW).
Resumable; output s05_events_cache.jsonl, one row per pool: {pid, ven, L, to, sw:[...], ml:[...]}."""
import sys
from common import *
SW = 4000
tg = jload("s05_targets.json")
head = jload("s01_meta.json")["head"]
have = {r["pid"] for r in jl_load("s05_events_cache.jsonl")}
todo = [t for t in tg if t["pid"] not in have]
print("targets", len(tg), "todo", len(todo), flush=True)
def swrow(l):
    return [int(l["blockNumber"], 16), int(l["transactionIndex"], 16), int(l["logIndex"], 16), l["transactionHash"], "0x" + l["topics"][2][-40:] if len(l["topics"]) > 2 else "", l["data"]]
for i in range(0, len(todo), 40):
    ch = todo[i:i + 40]
    q = []
    for t in ch:
        if t["ven"] == "v4":
            q.append([{"address": PM, "topics": [T_SWAP, t["pid"]], "fromBlock": hex(t["L"]), "toBlock": hex(min(head, t["L"] + SW))}])
            q.append([{"address": PM, "topics": [T_ML, t["pid"]], "fromBlock": hex(t["L"]), "toBlock": hex(head)}])
        else:
            q.append([{"address": t["pid"], "topics": [T_V3SWAP], "fromBlock": hex(t["L"]), "toBlock": hex(min(head, t["L"] + SW))}])
            q.append([{"address": t["pid"], "fromBlock": hex(t["L"]), "toBlock": hex(head)}])
    res = rpc.batch("eth_getLogs", q, n=20)
    rows = []
    for k, t in enumerate(ch):
        sw, ml = res[2 * k], res[2 * k + 1]
        if sw is None or ml is None: print("miss", t["pid"]); continue
        if t["ven"] == "v4":
            rows.append(dict(pid=t["pid"], ven="v4", L=t["L"], sw=[swrow(l) for l in sw], ml=[swrow(l) for l in ml]))
        else:
            other = [l for l in ml if l["topics"][0] != T_V3SWAP]
            # V3 Swap: topics sender, recipient; keep recipient in the 'sender' slot? keep both: topic1 sender(router), topic2 recipient
            rows.append(dict(pid=t["pid"], ven="v3", L=t["L"], sw=[swrow(l) + ["0x" + l["topics"][1][-40:]] for l in sw],
                             ml=[[int(l["blockNumber"], 16), int(l["transactionIndex"], 16), int(l["logIndex"], 16), l["transactionHash"], l["topics"][0][:10], l["topics"], l["data"]] for l in other]))
    jl_append(rows, "s05_events_cache.jsonl")
    print(i + len(ch), "/", len(todo), rpc.STATS, flush=True)
