#!/usr/bin/env python3
"""Population replay (logs only) of the v2.433 front-run on every family pool: 531 in-window (pools.pkl) + 102 forward (fwd_pools.pkl).
Same engine/trade logic as adv/replay.py (exact integer v4 math, our buy after the other swaps of its block, BUY_SLIP 3%, TP on the
engine's copy, sell at the head of its landing block, pulls), with the feed taken from the Swap logs (every buy = a feed buy of its
logged input) and the volume bot's FIRST buy (the first swap buying >= 0.01 ETH) given its real minOut rule: floor(0.99 x buy_out_int at
the launch state) (adv/quote.py: exact on 20/20 sampled pools). COMP = extra ETH some other front-runner buys in our block, ahead of us.
-> adv/popreplay.json"""
import sys, os, json, pickle, collections, statistics as st
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, EXP)
import advreplay as R
from fams import hours, MID_H
from advreplay import buy_int, sell_int
import v4math
P = pickle.load(open(os.path.join(EXP, "pools.pkl"), "rb")); FP = pickle.load(open(os.path.join(EXP, "fwd_pools.pkl"), "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
SP0 = 1604517591721945638372359205383840; L0 = 49279426163460954002188; BF = 20_215_000


def mkQ(p, src):
    b0 = p["b0"]
    swaps = [{"bn": x[0], "li": x[1], "a0": x[2], "a1": x[3], "sp": x[4], "L": x[5], "tx": x[7]} for x in p["sw"]]
    pulls = [m[0] for m in p["mls"] if m[4] < 0]
    pull = min(pulls) if pulls else None
    first_bot = next((s for s in swaps if s["a0"] < 0 and -s["a0"] >= 0.01e18), None)
    feed = []; feedtx = {}
    for s in swaps:
        if s["a0"] < 0:
            e = {"kind": "buy", "amt": -s["a0"], "bn": s["bn"], "idx": s["li"], "tx": s["tx"], "from": None}
            if first_bot is not None and s is first_bot:
                e["bot"] = True; e["min_out"] = int(v4math.buy_out_int(SP0, L0, -s["a0"], 2500) * 0.99)
            feed.append(e); feedtx[s["tx"]] = e
    return {"pid": p["pid"], "b0": b0, "fee": p["fee"], "sp0": p["sp0"], "L0": L0, "swaps": swaps, "pull": pull, "feed": feed, "feedtx": feedtx, "txs": {},
            "base_fee": {b0: BF}, "src": src, "h": hours(b0) if src == "inwin" else None, "first_bot": (first_bot["bn"] - b0, -first_bot["a0"] / 1e18) if first_bot else None}


def trade_comp(Q, K, X, comp=0, **kw):
    """an extra competitor buy of `comp` wei lands in our block just ahead of us: modelled as a synthetic swap appended to block B"""
    if comp == 0: return R.trade(Q, K, X, **kw)
    B = Q["b0"] + K + kw.get("land", 1)
    sp, L = R.chain_after(Q, B)
    sp2, out = buy_int(sp, L, comp, Q["fee"])
    syn = {"bn": B, "li": 10**6, "a0": -comp, "a1": out, "sp": sp2, "L": L, "tx": "comp"}
    # later logged swaps keep their logged post-states; the replay re-executes them from our state, so only the chain state at B changes
    Q2 = dict(Q); Q2["swaps"] = sorted(Q["swaps"] + [syn], key=lambda s: (s["bn"], s["li"]))
    e = {"kind": "buy", "amt": comp, "bn": B, "idx": 10**6, "tx": "comp", "from": None}
    Q2["feed"] = sorted(Q["feed"] + [e], key=lambda e: (e["bn"], e["idx"])); Q2["feedtx"] = dict(Q["feedtx"]); Q2["feedtx"]["comp"] = e
    return R.trade(Q2, K, X, **kw)


if __name__ == "__main__":
    Qs = [mkQ(p, "inwin") for p in P.values() if isf(p)] + [mkQ(p, "fwd") for p in FP.values() if isf(p)]
    Qs.sort(key=lambda q: q["b0"])
    print("pools", len(Qs), collections.Counter(q["src"] for q in Qs), "no bot buy:", [(q["pid"][:12], q["src"]) for q in Qs if q["first_bot"] is None])
    out = {}
    def run(tag, X_, K, comp=0, **kw):
        X = int(X_ * 1e18); rows = []
        for Q in Qs:
            r = trade_comp(Q, K, X, int(comp * 1e18), **kw); r["src"] = Q["src"]; r["h"] = Q["h"]; r["pid"] = Q["pid"]; rows.append(r)
        res = {}
        for part, sel in (("train", lambda r: r["src"] == "inwin" and r["h"] < MID_H), ("test", lambda r: r["src"] == "inwin" and r["h"] >= MID_H),
                          ("fwd", lambda r: r["src"] == "fwd"), ("all", lambda r: True)):
            rs = [r["ret"] for r in rows if sel(r) and r["ret"] is not None]
            if not rs: continue
            srt = sorted(rs, reverse=True)
            res[part] = {"n": len(rs), "mean": st.mean(rs), "median": st.median(rs), "pos": sum(1 for x in rs if x > 0) / len(rs), "ex_top3": st.mean(srt[3:]),
                         "pulled": sum(1 for r in rows if sel(r) and r["exit"] == "pulled"), "bot_rev": sum(1 for r in rows if sel(r) and r.get("bot_reverts")),
                         "exits": dict(collections.Counter(r["exit"] for r in rows if sel(r)))}
        out[tag] = res
        a = res["all"]
        print(f"{tag:40s} " + " | ".join(f"{k} n{v['n']} {100*v['mean']:+6.2f}% med {100*v['median']:+6.2f}% pos {v['pos']:.2f}" for k, v in res.items() if k != "all")
              + f" | ALL exits {a['exits']} botrev {a['bot_rev']}")
        return rows
    rows = run("X0.0012 K2 land1 lag1", 0.0012, 2)
    worst = sorted([r for r in rows if r["ret"] is not None], key=lambda r: r["ret"])[:8]
    print("  worst:", [(r["pid"][:10], r["src"], round(r["ret"], 4), r["exit"], r.get("S")) for r in worst])
    for X_ in (0.0012, 0.004, 0.006, 0.008, 0.010, 0.011, 0.012, 0.0125, 0.013):
        run(f"X{X_} K2 land1 lag2", X_, 2, lag=2)
    for K in range(2, 11):
        run(f"X0.0012 K{K} land1 lag1", 0.0012, K)
    for comp in (0.0012, 0.003, 0.006, 0.0105, 0.012):
        for X_ in (0.0012, 0.006):
            run(f"X{X_} K2 comp{comp}", X_, 2, comp=comp)
    for tp in (0.01, 0.03):
        run(f"X0.0012 K2 tp{tp}", 0.0012, 2, tp=tp)
    for H in (5, 10, 40):
        run(f"X0.0012 K2 H{H}", 0.0012, 2, H=H)
    json.dump(out, open(os.path.join(HERE, "popreplay.json"), "w"), indent=1)
