"""Stage 2: per 3.0 pool, the swaps with their transactions; T = the block of the bot's first buy (a buy whose tx calls the bot router
0x1cbaf24d with c1120e3d), its tx index; the bot's later buys; pulls (ModifyLiquidity with negative delta); outside buys (not the bot router,
not the sentinel) with size and block. -> parsed.pkl"""
import json, pickle, collections
from lib import *
D = json.load(open("pools.json")); kv_tx = KV("tx")
P = []
for p in D["pools"]:
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(),
                "sel": (t.get("input") or "")[2:10], "have_tx": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]
    q = dict(p); del q["ev"]
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None, nbot=len(bots),
             pull=pulls[0]["off"] if pulls else None, pullbn=pulls[0]["bn"] if pulls else None, pull_to=pulls[0]["to"] if pulls else None,
             pull_sel=pulls[0]["sel"] if pulls else None, missing=sum(1 for s in sw if s["bn"] <= p["L"] + 90 and not s["have_tx"]))
    P.append(q)
pickle.dump({"start": D["start"], "end": D["end"], "t0": D["t0"], "t1": D["t1"], "pools": P}, open("parsed.pkl", "wb"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"3.0 pools {len(P)}, with a bot buy {len(Ts)}, T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts)} max {max(Ts)}; "
      f"missing txs {sum(p['missing'] for p in P)}; pulled {sum(1 for p in P if p['pull'] is not None)}; "
      f"pulled before T {sum(1 for p in P if p['pull'] is not None and (p['T'] is None or p['pull'] < p['T']))}")
print("pull calls:", collections.Counter((p["pull_to"][:10], p["pull_sel"]) for p in P if p["pull"] is not None).most_common(5))
