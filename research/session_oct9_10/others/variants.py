#!/usr/bin/env python3
"""Exit/entry variants of the paper FOLLOW on the candidate families (same pricing as analyze.py): the hold (the last block the sell may be
sent after our buy: the engine's 2, then 5/10/20/30/60), the trigger (the engine's: the first real buy, 'late' if <= +6; or 'after_arm': the
first real buy after +6, ignoring earlier ones), land 1 fast. Prints a table; writes variants.json."""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math
Q96 = 1 << 96; STAKE = int(0.0012e18); GAS = int(4.2e12); TP = 0.01; MINW = int(2e14); ARM = 6; TMAX = 150
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "census.jsonl"))}
plogs = pickle.load(open(os.path.join(HERE, "cache_plogs.pkl"), "rb"))
inits = {l["topics"][1]: l for l in pickle.load(open(os.path.join(HERE, "cache_inits.pkl"), "rb"))["logs"]}


def paper(sw, mls, sp0, tick0, fee, trig_bn, land, lag, pull_bn, hold):
    B = trig_bn + land
    prev = [x for x in sw if x[0] < B]
    if prev: sp, L = prev[-1][4], prev[-1][5]
    else: sp, L = sp0, v4math.active_liquidity(tick0, [(lo, hi, d) for bn, lo, hi, d in mls if bn < B and d > 0])
    if L <= 0 or sp <= 0: return None
    tok = v4math.buy_out_int(sp, L, STAKE, fee)
    if tok <= 0: return None
    xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
    def ret_at(spc, Lc):
        if Lc <= 0: return -1.0
        return (v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tok, fee) - STAKE - GAS) / STAKE
    send = B + hold; why = "deadline"
    for x in sw:
        if B <= x[0] <= B + hold and x[2] < 0 and ret_at(x[4], x[5]) >= TP: send = x[0]; why = "tp"; break
    lb = send + lag
    if pull_bn is not None and pull_bn <= lb: return {"ret": -1.0 - GAS / STAKE, "why": "pulled", "send": send - B}
    pv = [x for x in sw if x[0] <= lb - 1]
    return {"ret": ret_at(pv[-1][4], pv[-1][5]) if pv else ret_at(sp, L), "why": why, "send": send - B}


def run(pid, hold, trig_mode):
    r = R[pid]; l = inits[pid]; d = l["data"]; b0 = r["b0"]
    ev = sorted(plogs[pid], key=lambda x: (x[0], x[1])); sw = []; mls = []; rem = []
    for bn, li, t0, snd, dd, th in ev:
        if t0 == T_SWAP:
            if snd[-40:] != RELAY: sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3)))
        else:
            mls.append((bn, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2))))
            if sgn(W(dd, 2)) < 0: rem.append(bn)
    real = [x for x in sw if -x[2] >= MINW and x[0] - b0 <= TMAX]
    if trig_mode == "engine":
        if not real or real[0][0] - b0 <= ARM: return None
        t = real[0][0]
    else:
        a = [x for x in real if x[0] - b0 > ARM]
        if not a: return None
        t = a[0][0]
    return paper(sw, mls, W(d, 3), sgn(W(d, 4)), W(d, 0), t, 1, 1, min(rem) if rem else None, hold)


FAMS = {
    "OURS-orig": lambda r: r["ours"] == "orig",
    "OURS-copy": lambda r: r["ours"] == "copy",
    "PM1444 fee1% ts200 v3.0": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0,
    "PM1444 fee1% ts200 v5.0": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 5.0,
    "PM1444 fee0.25% ts50 v2.433": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 2500 and r["ts"] == 50,
    "PM2276 fee0.01% ts1": lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 2276,
    "PMdirect 6276cbbe fee0.05% ts1": lambda r: r["sel"] == "0x6276cbbe" and r["fee"] == 500 and r["ts"] == 1,
    "create 60808060 fee0.25% ts25": lambda r: r["sel"] == "0x60808060" and r["fee"] == 2500,
    "0000ffff fresh-wallet fee0.25% ts25": lambda r: (r["to"] or "").startswith("0x0000ffffbe8efe") and r["fee"] == 2500,
    "ca11bde0 multicall3 fee0.25% ts25": lambda r: (r["to"] or "").startswith("0xca11bde0") and r["fee"] == 2500,
}
HOLDS = (2, 5, 10, 20, 30, 60)
out = {}
for name, f in FAMS.items():
    pids = [p for p, r in R.items() if r["logs"] and r["hooks"] == "0x" + "0" * 40 and f(r)]
    out[name] = {"n_pools": len(pids)}
    for tm in ("engine", "after_arm"):
        for h in HOLDS:
            res = [x for x in (run(p, h, tm) for p in pids) if x]
            if not res: continue
            v = [x["ret"] for x in res]
            out[name][f"{tm}/hold{h}"] = {"n": len(v), "mean": round(st.mean(v), 4), "median": round(st.median(v), 4), "pos": sum(1 for x in v if x > 0),
                                          "pulled": sum(1 for x in res if x["why"] == "pulled"), "tp": sum(1 for x in res if x["why"] == "tp")}
    print(name, out[name]["n_pools"])
    for k, v in out[name].items():
        if k != "n_pools": print(f"   {k:18s} n {v['n']:4d} mean {100*v['mean']:+6.2f}% median {100*v['median']:+6.2f}% pos {v['pos']:4d} pulled {v['pulled']:3d} tp {v['tp']:4d}")
json.dump(out, open(os.path.join(HERE, "variants.json"), "w"), indent=1)
