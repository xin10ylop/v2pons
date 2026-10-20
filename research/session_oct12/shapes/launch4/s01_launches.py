"""Every PoolManager Initialize of the last 12 h and its transaction; the shape table (to, calldata bytes, value, fee, tick spacing, hook, quote)
and the launches of the four watch shapes (targets in common.SHAPES). Caches: cache/s01_inits_cache.jsonl, cache/s01_txs_cache.jsonl.
Writes s01_meta.json, s01_launches.json; prints the table (s01_launches.out)."""
from common import *
import rpc, collections
HOURS = 12.0
head = int(rpc.call("eth_blockNumber", []), 16)
t_head = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
# find the block at t_head - 12 h by bisection on timestamps (about 25 calls)
target = t_head - int(HOURS * 3600)
lo, hi = head - 600_000, head
while lo < hi:
    mid = (lo + hi) // 2
    if int(rpc.call("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < target: lo = mid + 1
    else: hi = mid
start = lo
print(f"head {head} {utc(t_head)} UTC; 12 h back = block {start}; {(head - start) / (HOURS * 3600):.2f} blocks/s")
meta = {"head": head, "t_head": t_head, "start": start, "t_start": target}
json.dump(meta, open(J("s01_meta.json"), "w"))
inits = jl(C("s01_inits_cache.jsonl")); have = {(l["blockNumber"], l["logIndex"]) for l in inits}
done_to = max([int(l["blockNumber"], 16) for l in inits] + [start - 1])
step = 20_000
with open(C("s01_inits_cache.jsonl"), "a") as f:
    for a in range(start, head + 1, step):
        b = min(a + step - 1, head)
        for l in rpc.logs({"address": PM, "topics": [T_INIT]}, a, b):
            if (l["blockNumber"], l["logIndex"]) in have: continue
            have.add((l["blockNumber"], l["logIndex"])); inits.append(l); f.write(json.dumps(l) + "\n")
inits = [l for l in inits if start <= int(l["blockNumber"], 16) <= head]
print(len(inits), "Initialize logs in the window")
txs = {t["hash"]: t for t in jl(C("s01_txs_cache.jsonl"))}
need = sorted({l["transactionHash"] for l in inits} - set(txs))
with open(C("s01_txs_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for t in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20):
            if t: txs[t["hash"]] = t; f.write(json.dumps(t) + "\n")
groups = collections.defaultdict(list); L = []
for l in inits:
    t = txs.get(l["transactionHash"])
    if not t: continue
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hk = "0x%040x" % W(d, 2); sp = W(d, 3); tick = sgn(W(d, 4))
    c0 = "0x" + l["topics"][2][-40:]; c1 = "0x" + l["topics"][3][-40:]
    val = int(t["value"], 16); to = (t.get("to") or "create"); n = (len(t["input"]) - 2) // 2
    rec = {"pid": l["topics"][1], "lb": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "from": t["from"], "to": to,
           "sel": t["input"][2:10], "n": n, "value": val, "fee": fee, "ts": ts, "hook": hk, "sqrtP": sp, "tick": tick, "c0": c0, "c1": c1, "nonce": int(t["nonce"], 16)}
    L.append(rec)
    q = "ETH" if c0 == "0x" + "0" * 40 else c0[-6:] + "/" + c1[-6:]
    groups[(to[-8:], n, round(val / 1e18, 7), fee, ts, q[:13] if c0 != "0x" + "0" * 40 else "ETH", hk[-8:] if int(hk, 16) else "-")].append(rec)
rows = sorted(groups.items(), key=lambda kv: -len(kv[1]))
print(f"{'to':>8} {'bytes':>5} {'value':>10} {'fee':>8} {'ts':>5} {'quote c0/c1':<13} {'hook':<8} {'n':>4} {'wallets':>7}")
for k, v in rows[:45]:
    print(f"{k[0]:>8} {k[1]:>5} {k[2]:>10} {k[3]:>8} {k[4]:>5} {k[5]:<13} {k[6]:<8} {len(v):>4} {len({r['from'] for r in v}):>7}")
out = {}
for s, tos in SHAPES.items():
    out[s] = sorted([r for r in L if r["to"][-8:] in tos], key=lambda r: (r["lb"], r["li"]))
    v = out[s]
    print(f"\n{s} targets {tos}: {len(v)} launches, {len({r['from'] for r in v})} wallets, {len({r['tx'] for r in v})} txs")
    sub = collections.Counter((r["to"], r["sel"], r["n"], r["value"] / 1e18, r["fee"], r["ts"], r["hook"], r["c0"] if int(r["c0"], 16) else "ETH") for r in v)
    for k, c in sub.most_common(12): print("   ", c, k)
json.dump(out, open(J("s01_launches.json"), "w"))
print(rpc.STATS)
