#!/usr/bin/env python3
"""Outsider buys in the PM1444 families and what followed. A swap is the BOT's if its tx goes to the bot router 0x1cbaf24d or comes from a
wallet that ever sent to it (930 wallets; this includes the deployers, which pull through the router); the deployer's own swaps are DEP;
every other swap is an OUTSIDER's. Coverage: swaps with a fetched tx (census pools: launch..min(pull, +300); recent pools: ..min(pull, +600)).
Writes react.json."""
import sys, os, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load()
BOTW = {t["from"] for t in TX.values() if t["to"] == ROUTER}
COV = {"census": 300, "recent": 600}
def cls(v, s):
    t = TX.get(s["th"])
    if not t: return None, None
    if t["to"] == ROUTER or t["from"] in BOTW: return ("dep" if t["from"] == v["dep"] else "bot"), t
    if t["from"] == v["dep"]: return "dep", t
    return "out", t
OB = []
for v in P.values():
    lim = min(COV[v["src"]], v["pull"] if v["pull"] is not None else 10**9)
    v["cov"] = lim
    seq = []
    for s in v["sw"]:
        if s["rel"] > lim: break
        k, t = cls(v, s)
        seq.append((s, k, t))
    v["seq"] = seq
    for i, (s, k, t) in enumerate(seq):
        if k == "out" and s["eth"] > 0:
            later = seq[i + 1:]
            nb = [x[0]["rel"] for x in later if x[1] == "bot" and x[0]["eth"] > 0]
            ns = [x[0]["rel"] for x in later if x[1] == "bot" and x[0]["eth"] < 0]
            prior_out = [x for x in seq[:i] if x[1] == "out" and x[0]["eth"] >= 2e-4]
            OB.append({"fam": v["fam"], "src": v["src"], "pid": v["pid"], "b0": v["b0"], "rel": s["rel"], "eth": s["eth"], "wallet": t["from"], "to": t["to"], "inlen": t["inlen"],
                       "prio": t["prio"], "nonce": t["nonce"], "pull": v["pull"], "lag": (v["pull"] - s["rel"]) if v["pull"] is not None else None,
                       "next_bot_buy": nb[0] if nb else None, "next_bot_sell": ns[0] if ns else None, "first_real_outsider": not prior_out,
                       "same_block_pull": v["pull"] == s["rel"]})
json.dump(OB, open(os.path.join(HERE, "react.json"), "w"))
def q(xs, qs=(0, .1, .25, .5, .75, .9, 1)):
    xs = sorted(xs); return [xs[int(a * (len(xs) - 1))] for a in qs] if xs else None
print("swaps without a fetched tx inside coverage:", sum(1 for v in P.values() for s, k, t in v["seq"] if k is None))
for fam in ("v3.0", "v5.0", "v2.433"):
    pools = [v for v in P.values() if v["fam"] == fam]
    ob = [x for x in OB if x["fam"] == fam]
    print(f"\n=== {fam}: pools {len(pools)} (census {sum(1 for v in pools if v['src']=='census')}, recent {sum(1 for v in pools if v['src']=='recent')})")
    for lo, hi, name in ((0, 2e-4, "dust <0.0002"), (2e-4, 1e-3, "0.0002-0.001"), (1e-3, 0.01, "0.001-0.01"), (0.01, 99, ">=0.01")):
        xs = [x for x in ob if lo <= x["eth"] < hi]
        fx = [x for x in xs if x["first_real_outsider"]] if lo >= 2e-4 else xs
        pools_hit = len({x["pid"] for x in xs})
        lags = [x["lag"] for x in fx if x["lag"] is not None]
        w = collections.Counter(x["wallet"] for x in xs)
        print(f"  {name:13s}: buys {len(xs):5d} in {pools_hit:4d} pools, wallets {len(w):3d}; pull within 5/10/20/30/60 blocks of the (first) buy: " +
              "/".join(str(sum(1 for l in lags if l <= k)) for k in (5, 10, 20, 30, 60)) + f" of {len(fx)}; lag q0/10/25/50/75/90/100 {q(lags)}")
