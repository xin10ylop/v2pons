#!/usr/bin/env python3
"""Verifier step 2: re-price the candidate families with the independent pricer (vprice: sequential exact-input replay, sells by others
re-simulated) from the census's log cache (checked equal to fresh logs on 26 pools). Variants: the engine's trigger with the arming
lag ARM in (6, 9, 11); land 1 fast / land 2 slow; hold 2 / 30; PM1444 fixed entry; PM2276 minimum trigger. Concentration (top-5 share),
6-hour buckets. Writes v2_price.json."""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR); sys.path.insert(0, HERE)
from chain import T_SWAP, T_ML, W, sgn
import vprice
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
PL = pickle.load(open(os.path.join(HERE, "..", "cache_plogs.pkl"), "rb"))
INIT = {l["topics"][1]: l for l in pickle.load(open(os.path.join(HERE, "..", "cache_inits.pkl"), "rb"))["logs"]}
Z = "0x" + "0" * 40
FAMS = {
    "orig": lambda r: r["ours"] == "orig",
    "copy": lambda r: r["ours"] == "copy",
    "pm2276": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 2276,
    "v3": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0,
    "v5": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 5.0,
    "v2433": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 2500 and r["ts"] == 50,
    "pmdirect500": lambda r: r["sel"] == "0x6276cbbe" and r["fee"] == 500 and r["ts"] == 1,
    "ca11": lambda r: (r["to"] or "").startswith("0xca11bde0") and r["fee"] == 2500,
}
def prep(pid):
    r = R[pid]; d = INIT[pid]["data"]; b0 = r["b0"]
    sw = []; adds = []; rem = []
    for bn, li, t0, snd, dd, th in sorted(PL[pid], key=lambda x: (x[0], x[1])):
        if t0 == T_SWAP:
            if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), sgn(W(dd, 4))))
        else:
            lo, hi, dl = sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))
            if dl > 0 and th == r["tx"]: adds.append((lo, hi, dl))
            if dl < 0: rem.append(bn)
    tick0 = sgn(W(d, 4)); L0 = sum(dl for lo, hi, dl in adds if lo < tick0 <= hi)
    return {"b0": b0, "fee": W(d, 0), "sp0": W(d, 3), "L0": L0, "sw": sw, "pull": min(rem) if rem else None}
def trade(P, B, hold, lag):
    return vprice.follow(P["sw"], P["sp0"], P["L0"], P["fee"], B, hold, lag, P["pull"])
def engine_trig(P, arm, minw=2 * 10**14, after_arm=False):
    real = [s for s in P["sw"] if -s[2] >= minw and s[0] - P["b0"] <= 150]
    if after_arm: real = [s for s in real if s[0] - P["b0"] > arm]
    if not real or real[0][0] - P["b0"] <= arm: return None
    return real[0][0]
def summ(v, rows=None):
    if not v: return None
    x = [a["ret"] for a in v]; s = sorted(x, reverse=True)
    return {"n": len(x), "mean": round(st.mean(x), 4), "median": round(st.median(x), 4), "pos": sum(1 for a in x if a > 0), "pulled": sum(1 for a in v if a["why"] == "pulled"),
            "mean_wo_top5": round(st.mean(s[5:]), 4) if len(s) > 6 else None, "top5": [round(a, 3) for a in s[:5]], "worst": round(min(x), 4)}
B0 = 82878144
out = {}
for name, f in FAMS.items():
    pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == Z and f(r)]
    P = {p: prep(p) for p in pids}
    o = {"n_pools": len(pids), "gate_ok": sum(1 for p in pids if R[p]["fee"] < 10000 and (R[p].get("liq") or 0) >= 1e21)}
    variants = {}
    for arm in (6, 9, 11):
        for hold, land, lag in ((2, 1, 1), (2, 2, 2), (30, 1, 1), (30, 2, 2)):
            res = []
            for p in pids:
                t = engine_trig(P[p], arm)
                if t is None: continue
                x = trade(P[p], t + land, hold, lag)
                if x: res.append(dict(x, pid=p, b0=P[p]["b0"]))
            variants[f"arm{arm}/hold{hold}/land{land}_lag{lag}"] = res
    if name in ("v3", "v5", "v2433"):
        for K in (12, 16, 20, 25):
            for H in (25, 40):
                for lag in (1, 2):
                    res = [dict(x, pid=p, b0=P[p]["b0"]) for p in pids for x in [trade(P[p], P[p]["b0"] + K, H, lag)] if x]
                    variants[f"fixed+{K}/hold{H}/lag{lag}"] = res
    if name in ("pm2276", "orig", "pmdirect500"):
        for minw in (10**16, 5 * 10**16):
            for hold in (2, 30):
                res = []
                for p in pids:
                    t = engine_trig(P[p], 6, minw, after_arm=True)
                    if t is None: continue
                    x = trade(P[p], t + 1, hold, 1)
                    if x: res.append(dict(x, pid=p, b0=P[p]["b0"]))
                variants[f"min{minw/1e18:g}/hold{hold}/land1_lag1"] = res
    o["variants"] = {k: summ(v) for k, v in variants.items()}
    for k in list(variants):
        if k in ("arm6/hold2/land1_lag1", "arm6/hold30/land1_lag1", "min0.01/hold2/land1_lag1", "fixed+20/hold40/lag1", "fixed+16/hold40/lag1"):
            bk = collections.defaultdict(list)
            for x in variants[k]: bk[int((x["b0"] - B0) * 0.103 / 3600 // 6) * 6].append(x["ret"])
            o.setdefault("by6h", {})[k] = {h: (len(v), round(st.mean(v), 4), sum(1 for a in v if a > 0)) for h, v in sorted(bk.items())}
    o["per_pool_engine_hold2"] = [(x["pid"], round(x["ret"], 5), x["why"]) for x in variants["arm6/hold2/land1_lag1"]]
    o["per_pool_hold30"] = [(x["pid"], round(x["ret"], 5), x["why"], x["send"]) for x in variants["arm6/hold30/land1_lag1"]]
    out[name] = o
    print(f"== {name}: pools {len(pids)} (fee<1% & liq>=1e21: {o['gate_ok']})")
    for k, v in o["variants"].items():
        if v: print(f"   {k:28s} n {v['n']:4d} mean {100*v['mean']:+6.2f}% med {100*v['median']:+6.2f}% pos {v['pos']:4d} pulled {v['pulled']:3d} w/o top5 {100*(v['mean_wo_top5'] or 0):+6.2f}% top5 {v['top5']}")
    for k, v in o.get("by6h", {}).items(): print(f"   by 6h {k}: {v}")
json.dump(out, open(os.path.join(HERE, "v2_price.json"), "w"), indent=0)
