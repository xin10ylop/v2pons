"""Stage 5: the operator's reaction, re-measured from the chain (no reuse of other studies' tables):
 (i) an earlier stretch with outside buys before T (blocks 85850000..85916000, about 13:05-14:57 UTC Oct 11, where 0x7ae81404 and
     0x8c009ea5 bought early): every 3.0 pool, every non-bot, non-sentinel buy >= 0.00003 ETH at or before T (or with no T), the lag from it
     to the first pull, and whether the bot still bought;
 (ii) our slice (L > 86158232): every non-dust outside buy at any time and the pull lag; the pulls with no outside buy before them.
-> lags used by the front replay (s6)."""
import sys, json, collections, pickle
from lib import *
A, B = 85850000, 85916000
kv_tx = KV("tx")
def gettx(hashes):
    need = [h for h in dict.fromkeys(hashes) if h not in kv_tx.d]
    for i in range(0, len(need), 400):
        ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], 20)
        for h, t in zip(ch, res):
            if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
        kv_tx.flush()
    return [kv_tx.d.get(h) for h in hashes]
import os
if os.path.exists("s5_early_pools.json"): pools = json.load(open("s5_early_pools.json"))
else:
    ini = []
    for a in range(A, B + 1, 20000): ini += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 19999, B))
    cand = [l for l in ini if W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200]
    ltx = gettx([l["transactionHash"] for l in cand])
    pools = [{"pid": l["topics"][1], "L": int(l["blockNumber"], 16)} for l, t in zip(cand, ltx)
             if t and (t["to"] or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and int(t["value"], 16) == 3 * 10 ** 18]
    ev = collections.defaultdict(list)
    for i in range(0, len(pools), 15):
        g = pools[i:i + 15]
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, g[0]["L"], g[-1]["L"] + 400): ev[l["topics"][1]].append(l)
    for p in pools:
        p["ev"] = [{"kind": "swap" if l["topics"][0] == T_SWAP else "ml", "bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "data": l["data"]}
                   for l in sorted(ev[p["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))) if int(l["blockNumber"], 16) <= p["L"] + 400]
    json.dump(pools, open("s5_early_pools.json", "w"))
print(f"(i) early stretch {A}..{B}: 3.0 pools {len(pools)}", flush=True)
need = []
for p in pools:
    pulls = [e["bn"] for e in p["ev"] if e["kind"] == "ml" and sgn(W(e["data"], 2)) < 0]; pb = pulls[0] if pulls else p["L"] + 400
    need += [e["tx"] for e in p["ev"] if e["kind"] == "swap" and e["bn"] <= min(pb, p["L"] + 120)]
gettx(need)
def analyse(pools, label):
    pre = []; post = []; quiet_pulls = []
    for p in pools:
        sw = []
        for e in p["ev"]:
            if e["kind"] != "swap": continue
            t = kv_tx.d.get(e["tx"]); a0 = sgn(W(e["data"], 0))
            if not t: continue
            bot = a0 < 0 and (t["to"] or "").lower() == BOT and t["input"][2:10] == "c1120e3d"
            sw.append((e["bn"], a0 < 0, abs(a0) / 1e18, bot, t["from"].lower()))
        pulls = [e["bn"] for e in p["ev"] if e["kind"] == "ml" and sgn(W(e["data"], 2)) < 0]
        T = next((s[0] for s in sw if s[3]), None)
        out = [s for s in sw if s[1] and not s[3] and s[4] != SENTINEL and s[2] >= 0.00003 and (not pulls or s[0] <= pulls[0])]
        if out:
            s = out[0]; lag = pulls[0] - s[0] if pulls else None
            row = (p["L"], s[0] - p["L"], None if T is None else T - p["L"], round(s[2], 5), s[4][:10], lag, T is not None and T > s[0])
            (pre if (T is None or s[0] <= T) else post).append(row)
        elif pulls and pulls[0] <= p["L"] + 400: quiet_pulls.append((p["L"], pulls[0] - p["L"], None if T is None else T - p["L"]))
    for name, rows in (("before T (or no T)", pre), ("after T", post)):
        lags = [r[5] for r in rows if r[5] is not None]
        print(f"  {label}: first non-dust outside buy {name}: pools {len(rows)}, pulled {len(lags)}; lag min {min(lags) if lags else None} "
              f"p25/50/75 {pct(lags,.25)}/{pct(lags,.5)}/{pct(lags,.75)} max {max(lags) if lags else None}; sorted {sorted(lags)}; bot bought after it {sum(1 for r in rows if r[6])}")
        for r in rows: print("     L, buy off, T, ETH, wallet, pull lag, bot bought after:", r)
    print(f"  {label}: pulls with no non-dust outside buy before them: {len(quiet_pulls)} {quiet_pulls}")
    return pre, post
pre_e, post_e = analyse(pools, "early stretch")
D = pickle.load(open("parsed.pkl", "rb"))
slice_pools = json.load(open("pools.json"))["pools"]
print(f"\n(ii) our slice: 3.0 pools {len(slice_pools)}")
pre_s, post_s = analyse(slice_pools, "our slice")
lags = sorted(r[5] for r in pre_e + pre_s if r[5] is not None)
json.dump({"pre_T_lags": lags, "post_T_lags": sorted(r[5] for r in post_e + post_s if r[5] is not None)}, open("s5_lags.json", "w"))
print(f"\npre-T lags (both): n {len(lags)} min {lags[0] if lags else None} median {pct(lags,.5) if lags else None}: {lags}")
