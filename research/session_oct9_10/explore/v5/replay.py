#!/usr/bin/env python3
"""Exact feed replay of the PM1444 v5.0 rule (launch+3, TP 5%, H 60) on v5/cache.pkl (22 pools: 13 in-window, 5 forward, 4 fresh).
Engine/trade logic = explore/adv/advreplay.py (adapted from yday/follow.py): full blocks b0..b0+80 in feed order, a feed BUY = value>0 and
the token in calldata (0.8 on_buy), BUY_SLIP 3% minOut from the engine's copy at the fire block, our buy lands at F+land AFTER every other
swap of its block, TP on the engine's copy at every feed buy >= 0.0002 ETH, sell lands send+lag priced at the head of its block, later swaps
re-executed by input with the volume bot's buys (router 0x1cbaf24d, c1120e3d) reverting under their logged minOut, wallets that bought
behind us sell the same fraction; gas 103,900 x 2 x base fee.
NEW HERE: the operator's reaction to an outsider buy. v5/react2.py: of 65 v5.0 census pools where a non-operator buy (> 2e-5 ETH, not via
the operator's route) landed before any pull, 61 were pulled (100% of the liquidity) 4..24 blocks later; the 4 not pulled were 3e-5..1e-4 ETH.
Our buy (0.0012 / 0.012 ETH via FlipRelay) is such a buy, so  'react' = pull at our buy's block + lag, lag drawn from those 61 lags;
the trade's expected return = P(lag <= S - B) x (-100% - gas) + (1 - P) x the no-reaction replay.  -> v5/replay.json"""
import sys, os, json, pickle, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EXP, "adv")); sys.path.insert(0, EXP)
import advreplay as R
LAGS = json.load(open(os.path.join(HERE, "lags.json")))["lags"]


def react(r, X):
    if r["ret"] is None or r["exit"] in ("buy_reverted", "pull_before_buy", "pulled"): return r["ret"], None
    span = r["S"] - r["B"]
    p = sum(1 for L in LAGS if L <= span) / len(LAGS)
    gas_frac = -1 - r["ret"] if False else None
    loss = -1 - (R.BUY_GAS + R.SELL_GAS) * 2.0e7 / X
    return (1 - p) * r["ret"] + p * loss, p


if __name__ == "__main__":
    D = pickle.load(open(os.path.join(HERE, "cache.pkl"), "rb"))
    Qs = sorted([R.prep(P) for P in D.values()], key=lambda q: q["b0"])
    out = {"pools": [], "variants": {}}
    for Q in Qs:
        bots = [(e["bn"] - Q["b0"], round(e["amt"] / 1e18, 5)) for e in Q["feed"] if e["kind"] == "buy" and e["amt"] >= R.MIN_TRIGGER_WEI][:4]
        print(f"  {Q['src']:5s} {Q['pid'][:12]} b0 {Q['b0']} nonce {Q['nonce']} replay_err {Q['replay_err']:.1e} unseen {Q['unseen'][:3]} first_bot {Q['first_bot']} pull {(Q['pull'] - Q['b0']) if Q['pull'] else None} feedbuys {bots}")
        out["pools"].append({k: Q[k] for k in ("pid", "b0", "src", "nonce", "replay_err", "first_bot")} | {"pull": (Q["pull"] - Q["b0"]) if Q["pull"] else None, "unseen": Q["unseen"][:5]})
    V = []
    for X_ in (0.0012, 0.012):
        for land in (1, 2):
            for lag in (1, 2):
                V.append((X_, 3, 0.05, 60, land, lag, "buys", "fresh"))
        V += [(X_, 3, 0.05, 60, 1, 1, "sells", "fresh"), (X_, 3, 0.05, 60, 1, 1, "buys", "strict"),
              (X_, 2, 0.01, 49, 1, 1, "buys", "fresh"), (X_, 2, 0.01, 49, 2, 2, "buys", "fresh"), (X_, 2, 0.01, 49, 1, 1, "sells", "fresh")]
    for (X_, K, tp, H, land, lag, view, mode) in V:
        X = int(X_ * 1e18); rows = []
        for Q in Qs:
            r = R.trade(Q, K, X, land=land, tp=tp, H=H, lag=lag, view=view, mode=mode); r["pid"] = Q["pid"]; r["src"] = Q["src"]
            r["cheap"] = R.cheap(Q, K, X, tp=tp, H=H)
            r["ret_react"], r["p_pull"] = react(r, X)
            rows.append(r)
        rs = [r["ret"] for r in rows if r["ret"] is not None]; rr = [r["ret_react"] for r in rows if r["ret_react"] is not None]
        cs = [(r["ret"], r["cheap"]) for r in rows if r["ret"] is not None and r["cheap"] is not None]
        k = f"X{X_}|K{K}|TP{tp}|H{H}|land{land}|lag{lag}|{view}|{mode}"
        v = {"n": len(rs), "mean": st.mean(rs), "median": st.median(rs), "min": min(rs), "pos": sum(1 for x in rs if x > 0) / len(rs),
             "mean_react": st.mean(rr), "median_react": st.median(rr), "mean_p_pull": st.mean([r["p_pull"] for r in rows if r["p_pull"] is not None]),
             "cheap_mean": st.mean([b for a, b in cs]), "max_abs_diff_vs_cheap": max(abs(a - b) for a, b in cs),
             "exits": dict(collections.Counter(r["exit"] for r in rows)), "bot_reverts": sum(1 for r in rows if r.get("bot_reverts")), "rows": rows}
        out["variants"][k] = v
        print(f"{k:48s} n {v['n']:2d} mean {v['mean']:+.4f} med {v['median']:+.4f} min {v['min']:+.4f} pos {v['pos']:.2f} | cheap {v['cheap_mean']:+.4f} max|d| {v['max_abs_diff_vs_cheap']:.4f} "
              f"| REACT mean {v['mean_react']:+.4f} med {v['median_react']:+.4f} P(pull<=sell) {v['mean_p_pull']:.2f} | exits {v['exits']} botrev {v['bot_reverts']}")
    for k in ("X0.012|K3|TP0.05|H60|land1|lag1|buys|fresh", "X0.0012|K3|TP0.05|H60|land1|lag1|buys|fresh", "X0.012|K2|TP0.01|H49|land1|lag1|buys|fresh"):
        print("per pool", k)
        for Q, r in zip(Qs, out["variants"][k]["rows"]):
            print(f"   {Q['src']:5s} {Q['pid'][:12]} pull {(Q['pull'] - Q['b0']) if Q['pull'] else None} -> {r['exit']:8s} B +{r.get('B')} send +{r.get('send')} S +{r.get('S')} "
                  f"ret {100*r['ret']:+.2f}% cheap {100*(r.get('cheap') or 0):+.2f}% tp_feed {r.get('tp_feed')} P(pull<=S) {r['p_pull']} react {100*r['ret_react']:+.2f}% botrev {r.get('bot_reverts')}")
    json.dump(out, open(os.path.join(HERE, "replay.json"), "w"), indent=1, default=str)
