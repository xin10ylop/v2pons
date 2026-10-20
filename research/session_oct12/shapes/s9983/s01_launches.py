"""Every PoolManager Initialize of the last 12 h; the ones whose hook ends 4924e0cc or whose currency0/currency1 is the quote token 0x32ac8c..,
with their transactions; the shape table for them (to, calldata bytes, value, fee, tick spacing, hook, quote) and the launches of the 9983bb8c
target. Also: every Initialize with the quote token as currency0 or currency1 over the last 8 days (history of the quote).
Caches: cache/s01_inits_cache.jsonl, cache/s01_qinits_cache.jsonl, cache/s01_txs_cache.jsonl. Writes s01_meta.json, s01_launches.json."""
from common import *
import rpc, collections
HOURS = 12.0
head = int(rpc.call("eth_blockNumber", []), 16)
t_head = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
def ts_of(bn): return int(rpc.call("eth_getBlockByNumber", [hex(bn), False])["timestamp"], 16)
def block_at(t):
    lo, hi = max(1, head - 8_000_000), head
    while lo < hi:
        mid = (lo + hi) // 2
        if ts_of(mid) < t: lo = mid + 1
        else: hi = mid
    return lo
start = block_at(t_head - int(HOURS * 3600))
start8 = block_at(t_head - 8 * 86400)
print(f"head {head} {utc(t_head)} UTC; 12 h back = block {start}; 8 d back = block {start8}; {(head - start) / (HOURS * 3600):.2f} blocks/s")
meta = {"head": head, "t_head": t_head, "start": start, "t_start": t_head - int(HOURS * 3600), "start8": start8}
json.dump(meta, open(J("s01_meta.json"), "w"))
# 1. all Initialize logs in 12 h
inits = jl(C("s01_inits_cache.jsonl")); have = {(l["blockNumber"], l["logIndex"]) for l in inits}
done = int(open(C("s01_inits_done.txt")).read()) if os.path.exists(C("s01_inits_done.txt")) else start - 1
step = 20_000
with open(C("s01_inits_cache.jsonl"), "a") as f:
    for a in range(max(start, done + 1), head + 1, step):
        b = min(a + step - 1, head)
        for l in rpc.logs({"address": PM, "topics": [T_INIT]}, a, b):
            if (l["blockNumber"], l["logIndex"]) in have: continue
            have.add((l["blockNumber"], l["logIndex"])); inits.append(l); f.write(json.dumps(l) + "\n")
        open(C("s01_inits_done.txt"), "w").write(str(b))
inits = [l for l in inits if start <= int(l["blockNumber"], 16) <= head]
print(len(inits), "Initialize logs in 12 h")
# 2. the quote token's Initialize history (8 d), currency0 or currency1
q = jl(C("s01_qinits_cache.jsonl")); qh = {(l["blockNumber"], l["logIndex"]) for l in q}
qdone = int(open(C("s01_qinits_done.txt")).read()) if os.path.exists(C("s01_qinits_done.txt")) else start8 - 1
with open(C("s01_qinits_cache.jsonl"), "a") as f:
    for a in range(max(start8, qdone + 1), head + 1, 500_000):
        b = min(a + 499_999, head)
        for flt in ({"address": PM, "topics": [T_INIT, None, topic_addr(QUOTE)]}, {"address": PM, "topics": [T_INIT, None, None, topic_addr(QUOTE)]}):
            for l in rpc.logs(flt, a, b):
                if (l["blockNumber"], l["logIndex"]) in qh: continue
                qh.add((l["blockNumber"], l["logIndex"])); q.append(l); f.write(json.dumps(l) + "\n")
        open(C("s01_qinits_done.txt"), "w").write(str(b))
print(len(q), "Initialize logs with the quote token in 8 d")
def dec(l):
    d = l["data"]
    return {"pid": l["topics"][1], "lb": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "fee": W(d, 0), "ts": sgn(W(d, 1)),
            "hook": "0x%040x" % W(d, 2), "sqrtP": W(d, 3), "tick": sgn(W(d, 4)), "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:]}
sel_ = {}
for l in inits + q:
    r = dec(l)
    if r["hook"].endswith(HOOK_TAIL) or QUOTE in (r["c0"], r["c1"]): sel_[(r["tx"], r["li"])] = r
print(len(sel_), "selected (hook ...4924e0cc or quote token)")
txs = {t["hash"]: t for t in jl(C("s01_txs_cache.jsonl"))}
need = sorted({r["tx"] for r in sel_.values()} - set(txs))
with open(C("s01_txs_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for t in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20):
            if t: txs[t["hash"]] = t; f.write(json.dumps(t) + "\n")
L = []
for r in sel_.values():
    t = txs.get(r["tx"])
    if not t: continue
    r.update({"from": t["from"], "to": t.get("to") or "create", "sel": t["input"][2:10], "n": (len(t["input"]) - 2) // 2, "value": int(t["value"], 16), "nonce": int(t["nonce"], 16)})
    L.append(r)
L.sort(key=lambda r: (r["lb"], r["li"]))
groups = collections.defaultdict(list)
for r in L:
    qq = "ETH" if r["c0"] == Z else ("Q/coin" if r["c0"] == QUOTE else "coin/Q" if r["c1"] == QUOTE else r["c0"][2:8] + "/" + r["c1"][2:8])
    groups[(r["to"][-8:], r["sel"], r["n"], round(r["value"] / 1e18, 7), r["fee"], r["ts"], qq, r["hook"][-8:] if int(r["hook"], 16) else "-", r["sqrtP"])].append(r)
print(f"\n{'to':>8} {'sel':8} {'bytes':>5} {'value':>9} {'fee':>7} {'ts':>4} {'quote c0/c1':<13} {'hook':<8} {'sqrtP':>36} {'n':>4} {'wal':>4} {'12h':>4}  first..last block")
for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(f"{k[0]:>8} {k[1]:8} {k[2]:>5} {k[3]:>9} {k[4]:>7} {k[5]:>4} {k[6]:<13} {k[7]:<8} {k[8]:>36} {len(v):>4} {len({r['from'] for r in v}):>4} {sum(1 for r in v if r['lb'] >= start):>4}  {v[0]['lb']}..{v[-1]['lb']}")
core = [r for r in L if r["to"][-8:] == TARGET_TAIL]
print(f"\ntarget ...{TARGET_TAIL}: {len(core)} launches ({sum(1 for r in core if r['lb'] >= start)} in 12 h), first {core[0]['lb'] if core else None} "
      f"({utc(ts_of(core[0]['lb'])) if core else ''} UTC), wallets {len({r['from'] for r in core})}")
bph = (head - start) / (HOURS * 3600) * 3600
print("   launches per 6 h (back from the head):", [sum(1 for r in core if head - (k + 1) * 6 * bph < r["lb"] <= head - k * 6 * bph) for k in range(32)][::-1])
c12 = [r for r in core if r["lb"] >= start]
print(f"   12 h: {len(c12)} launches, {len({r['from'] for r in c12})} wallets; by bytes {collections.Counter(r['n'] for r in c12).most_common()}")
print(f"   3 h before the 18:52 watch (blocks 86793586..86899468): {sum(1 for r in core if 86793586 <= r['lb'] <= 86899468)}")
for w, c in collections.Counter(r["from"] for r in core).most_common(12): print(f"   {w} {c} launches, nonces {sorted(r['nonce'] for r in core if r['from'] == w)[:12]}")
print("   targets:", collections.Counter(r["to"] for r in core).most_common())
print("   (bytes, sel):", collections.Counter((r["n"], r["sel"]) for r in core).most_common())
print("   hooks:", collections.Counter(r["hook"] for r in core).most_common(), "quotes c0:", collections.Counter(r["c0"] for r in core).most_common(3))
other_hook = [r for r in L if r["hook"].endswith(HOOK_TAIL) and r["to"][-8:] != TARGET_TAIL]
print(f"same hook through other targets: {len(other_hook)}", collections.Counter((r["to"], r["sel"]) for r in other_hook).most_common(8))
json.dump({"meta": meta, "core": core, "all": L}, open(J("s01_launches.json"), "w"))
print(rpc.STATS)
