"""Stage 1: every volume-bot 3.0 launch in the last N hours (default 48): Initialize on the PoolManager with currency0 = ETH, fee 10000,
spacing 200, no hook, sqrtP 679394651928963067279918579724198; launch tx to the PositionManager, value 3.0 ETH, 1,444 bytes.
Then every Swap / ModifyLiquidity log of each pool from L to L+SPAN (600). Writes cache/launches.json and cache/events.json.
Block times: sampled at every 50,000-block chunk boundary and interpolated (logs carry no timestamp on this node)."""
import sys, json, os, collections
from lib import *
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 48
SPAN = 600; CH = 50000
kv_init = KV("init_chunks"); kv_bt = KV("block_ts"); kv_tx = KV("tx"); kv_ev = KV("ev_groups")
head = int(rpc("eth_blockNumber", []), 16)
meta_p = os.path.join(CACHE, "meta.json")
if os.path.exists(meta_p) and "--refresh" not in sys.argv:
    meta = json.load(open(meta_p)); head = meta["head"]; start = meta["start"]
else:
    hb = rpc("eth_getBlockByNumber", [hex(head), False]); ob = rpc("eth_getBlockByNumber", [hex(head - 100000), False])
    bps = 100000 / (int(hb["timestamp"], 16) - int(ob["timestamp"], 16))
    start = head - int(hours * 3600 * bps)
    meta = {"head": head, "start": start, "hours": hours}; json.dump(meta, open(meta_p, "w"))
print(f"head {head}, start {start} ({(head-start)} blocks)", flush=True)
# block timestamps at chunk boundaries
pts = list(range(start, head, CH)) + [head]
need = [b for b in pts if str(b) not in kv_bt.d]
for b, r in zip(need, batch([("eth_getBlockByNumber", [hex(b), False]) for b in need])):
    if r: kv_bt.put(str(b), int(r["timestamp"], 16))
kv_bt.flush()
TS = sorted((int(k), v) for k, v in kv_bt.d.items())
def ts_of(bn):
    for (b0, t0), (b1, t1) in zip(TS, TS[1:]):
        if b0 <= bn <= b1: return t0 + (t1 - t0) * (bn - b0) / max(1, b1 - b0)
    return TS[-1][1] + (bn - TS[-1][0]) / 9.8
ini = []
for a in range(start, head + 1, CH):
    k = f"{a}"
    if k not in kv_init.d:
        b = min(a + CH - 1, head)
        r = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b)
        kv_init.put(k, [x for x in r if W(x["data"], 0) == 10000 and sgn(W(x["data"], 1)) == 200 and W(x["data"], 2) == 0 and W(x["data"], 3) == SQRT30])
        kv_init.flush(); print(f"  init {a}: {len(r)} ETH inits, {len(kv_init.d[k])} at the 3.0 shape", flush=True)
    ini += kv_init.d[k]
print("3.0-shape Initialize logs:", len(ini), flush=True)
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
    return [kv_tx.d.get(h) for h in hashes]
ltx = gettx([l["transactionHash"] for l in ini])
pools = []; other = collections.Counter()
for l, t in zip(ini, ltx):
    if not t: other["no tx"] += 1; continue
    ok = (t.get("to") or "").lower() == POSM and int(t["value"], 16) == 3 * 10 ** 18 and (len(t["input"]) - 2) // 2 == 1444
    if not ok: other[((t.get("to") or "")[:10], int(t["value"], 16) / 1e18, (len(t["input"]) - 2) // 2)] += 1; continue
    L = int(l["blockNumber"], 16)
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "L": L, "lti": int(l["transactionIndex"], 16), "ts": round(ts_of(L)),
                  "launch_tx": l["transactionHash"], "launcher": t["from"].lower(), "launcher_nonce": int(t["nonce"], 16)})
print("3.0 launches:", len(pools), "other shapes:", dict(other), flush=True)
pools.sort(key=lambda p: p["L"])
json.dump({"head": head, "start": start, "pools": pools}, open(os.path.join(CACHE, "launches.json"), "w"))
# events per group of 20 pools
ev = collections.defaultdict(list)
for i in range(0, len(pools), 20):
    g = pools[i:i + 20]; k = g[0]["pid"] + ":" + str(len(g))
    if k not in kv_ev.d:
        a = g[0]["L"]; b = min(g[-1]["L"] + SPAN, head)
        r = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b)
        kv_ev.put(k, [{"pid": x["topics"][1], "kind": "swap" if x["topics"][0] == T_SWAP else "ml", "bn": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
                       "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"], "sender": "0x" + x["topics"][2][-40:], "data": x["data"]} for x in r])
        kv_ev.flush(); print(f"  events {i + len(g)}/{len(pools)}: {len(r)} logs", flush=True)
    for x in kv_ev.d[k]: ev[x["pid"]].append(x)
for p in pools:
    p["ev"] = sorted((x for x in ev[p["pid"]] if x["bn"] <= p["L"] + SPAN), key=lambda x: (x["bn"], x["li"]))
    p["span"] = min(SPAN, head - p["L"])
json.dump({"head": head, "start": start, "pools": pools}, open(os.path.join(CACHE, "events.json"), "w"))
print("done; pools with events:", sum(1 for p in pools if p["ev"]), flush=True)
