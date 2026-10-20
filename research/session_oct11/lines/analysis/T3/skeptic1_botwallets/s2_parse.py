"""Stage 2: per pool the swaps with their transactions, T (block offset of the bot's first buy: a buy whose tx calls the bot's router 0x1cbaf24d
with c1120e3d), its wallet, size; the bot's later buys; pulls (ModifyLiquidity with negative delta); outside buys before T.
Pools with L >= 85,728,764 are dropped: the finder's Initialize scan started there (its first pool L = 85,728,798), so every pool kept here
is one the finder did not use. -> parsed.pkl"""
import json, pickle, collections
from lib import *
FINDER_START = 85728764
import os
D = json.load(open("pools.json")); kv_tx = KV("tx")
if os.path.exists("pools_late.json"): D["pools"] += json.load(open("pools_late.json"))["pools"]   # the newest pools, after the finder's last (s1b_late.py)
P = []
for p in D["pools"]:
    if FINDER_START <= p["L"] <= 86150251: continue   # the finder's range (its first and last pool)
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have_tx": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None, bot2=bots[1]["off"] if len(bots) > 1 else None,
             nbot=len(bots), pull=pulls[0]["off"] if pulls else None, pull_bn=pulls[0]["bn"] if pulls else None, pull_eoa=pulls[0]["eoa"] if pulls else None,
             pull_sel=pulls[0]["sel"] if pulls else None)
    P.append(q)
bw = collections.Counter(s["eoa"] for p in P for s in p["sw"] if s["bot"])
pickle.dump({"pools": P, "botwallets_pools": dict(bw)}, open("parsed.pkl", "wb"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"pools {len(P)} (L {P[0]['L']}..{P[-1]['L']}), with a bot buy {len(Ts)}, T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts)} max {max(Ts)}; "
      f"missing txs {sum(1 for p in P for s in p['sw'] if not s['have_tx'] and s['off'] <= 120)}; pulled by L+200 {sum(1 for p in P if p['pull'] is not None)}")
print("bot buyer wallets in these pools:", len(bw))
