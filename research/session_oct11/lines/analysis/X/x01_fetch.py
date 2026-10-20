"""Fetch, Oct 10 00:00 UTC .. head: every 2.433 / 3.0 launch of the volume bot (Initialize at the line's price, ETH pair, no hook; launch tx to
the PositionManager with the line's value and 1,444 bytes), every Swap and ModifyLiquidity log of those pools to launch + SPAN, the
transactions of the swaps to launch + TXSPAN and of every liquidity log; our relay's swaps; block timestamps of the launch blocks.
Stages are cached (x01_*.json, txcache.jsonl); rerun resumes."""
import sys, json, time, os
from rpc import call, batch, logs, STATS
from xcommon import *
SPAN = 1200; TXSPAN = 400
def st(name): return os.path.join(HERE, "x01_" + name + ".json")
def load(name): return json.load(open(st(name))) if os.path.exists(st(name)) else None
def save(name, obj): json.dump(obj, open(st(name), "w"))
def log(*a): print(time.strftime("%H:%M:%S"), *a, f"[posts {STATS['posts']} 429s {STATS['r429']}]", flush=True)

meta = load("meta")
if not meta:
    head = int(call("eth_blockNumber", []), 16) - 30
    th = int(call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    lo, hi = head - 2_200_000, head
    while lo < hi:
        mid = (lo + hi) // 2
        if int(call("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < T_START: lo = mid + 1
        else: hi = mid
    meta = {"head": head, "head_ts": th, "start": lo}
    save("meta", meta)
head, start = meta["head"], meta["start"]
log("range", start, head, utc(T_START), "..", utc(meta["head_ts"]))

inits = load("inits")
if inits is None:
    inits = []
    for a in range(start, head + 1, 20000):
        inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, head))
    save("inits", inits)
log("ETH-pair initializes", len(inits))
txc = TxCache(os.path.join(HERE, "txcache.jsonl"))
pools = load("pools")
if pools is None:
    cand = []
    for l in inits:
        d = l["data"]; fee, ts, hooks, sp = W(d, 0), sgn(W(d, 1)), W(d, 2), W(d, 3)
        if hooks == 0 and sp in SP: cand.append((l, fee, ts, sp))
    lt = txc.get([l["transactionHash"] for l, *_ in cand], batch)
    pools, other = [], []
    for l, fee, ts, sp in cand:
        tx = lt.get(l["transactionHash"])
        v = int(tx["value"], 16) if tx else -1; clen = (len(tx["input"]) - 2) // 2 if tx else -1
        rec = {"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
               "fee": fee, "tsp": ts, "sp0": sp, "clen": clen, "value": v, "from": (tx or {}).get("from"), "nonce": int(tx["nonce"], 16) if tx else None, "to": (tx or {}).get("to")}
        if tx and (tx.get("to") or "").lower() == POSM and v in VAL and clen == 1444:
            rec["line"] = VAL[v]; pools.append(rec)
        else: other.append(rec)
    bl = sorted(set(p["lb"] for p in pools))
    hdr = batch("eth_getBlockByNumber", [[hex(b), False] for b in bl], 40)
    bts = {b: int(h["timestamp"], 16) for b, h in zip(bl, hdr) if h}
    for p in pools: p["ts"] = bts.get(p["lb"])
    pools.sort(key=lambda p: (p["lb"], p["li"]))
    save("pools", pools); save("other_same_price", other)
log("line launches", len(pools), {k: sum(1 for p in pools if p["line"] == k) for k in ("2.433", "3.0")})

ours = load("ours")
if ours is None:
    ours = []
    for a in range(start - 1000, head + 1, 100000):
        ours += logs({"address": PM, "topics": [T_SWAP, None, pad(RELAY)]}, a, min(a + 99999, head))
    save("ours", ours)
log("our relay swaps", len(ours))

ev = load("ev") or {}
grp_done = set(ev.get("_done", []))
i = 0
while i < len(pools):
    j = i
    while j + 1 < len(pools) and pools[j + 1]["lb"] - pools[i]["lb"] < 2500 and j + 1 - i < 30: j += 1
    key = f"{pools[i]['pid']}:{pools[j]['pid']}"
    if key not in grp_done:
        grp = pools[i:j + 1]; ids = [p["pid"] for p in grp]; bypid = {p["pid"]: p for p in grp}
        a, b = grp[0]["lb"], min(head, grp[-1]["lb"] + SPAN)
        for x in logs({"address": PM, "topics": [[T_SWAP, T_ML], ids]}, a, b):
            p = bypid[x["topics"][1]]; bn = int(x["blockNumber"], 16)
            if p["lb"] <= bn <= p["lb"] + SPAN:
                ev.setdefault(p["pid"], []).append({"k": "sw" if x["topics"][0] == T_SWAP else "ml", "bn": bn, "li": int(x["logIndex"], 16), "ti": int(x["transactionIndex"], 16),
                                                    "tx": x["transactionHash"], "sender": "0x" + x["topics"][2][-40:], "data": x["data"]})
        grp_done.add(key)
        if len(grp_done) % 20 == 0:
            ev["_done"] = sorted(grp_done); save("ev", ev); log(f"  pools {i}-{j} of {len(pools)}")
    i = j + 1
ev["_done"] = sorted(grp_done); save("ev", ev)
log("events fetched for", len([k for k in ev if k != "_done"]), "pools")
pb = {p["pid"]: p for p in pools}
need = []
for pid, es in ev.items():
    if pid == "_done": continue
    lb = pb[pid]["lb"]
    for e in es:
        if e["k"] == "ml" or e["bn"] - lb <= TXSPAN: need.append(e["tx"])
need += [l["transactionHash"] for l in ours]
log("transactions needed", len(set(need)), "cached", sum(1 for h in set(need) if h in txc.d))
txc.get(need, batch, 40, progress=lambda a, b: log(f"  tx {a}/{b}"))
log("done")
