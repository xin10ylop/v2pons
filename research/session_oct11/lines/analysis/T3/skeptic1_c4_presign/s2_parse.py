"""Stage 2: per pool the swaps with their txs; T = offset of the bot's first buy (a buy, ETH in, whose tx calls the bot router 0x1cbaf24d with
c1120e3d); its wallet, size, calldata words; later bot buys; pulls (ModifyLiquidity with negative delta); outside buys (not a bot wallet, not the
sentinel 0xe71a69f4.., not ours) with size and offset. -> parsed_<slice>.pkl.  usage: s2_parse.py <slice>"""
import sys, json, pickle, collections
from lib import *
name = sys.argv[1]; D = json.load(open(f"pools_{name}.json")); kv_tx = KV("tx")
P = []
for p in D["pools"]:
    sw, ml = [], []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have_tx": bool(t), "router": e["sender"].lower()}
        if e["kind"] == "swap":
            a0, a1 = sgn(W(e["data"], 0)), sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            if r["bot"]:
                inp = t["input"]; r["words"] = [int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16) for i in range((len(inp) - 10) // 64)]; r["inlen"] = (len(inp) - 2) // 2
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             Ttx=bots[0]["tx"] if bots else None, buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             Twords=bots[0]["words"] if bots else None, Tinlen=bots[0]["inlen"] if bots else None, Trouter=bots[0]["router"] if bots else None,
             bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots), pull=pulls[0]["off"] if pulls else None,
             pull_eoa=pulls[0]["eoa"] if pulls else None, pull_sel=(pulls[0]["to"][:10] + ":" + pulls[0]["sel"]) if pulls else None)
    P.append(q)
botw = set(s["eoa"] for p in P for s in p["sw"] if s["bot"])
for p in P:
    p["outside"] = [dict(off=s["off"], bn=s["bn"], ti=s["ti"], eoa=s["eoa"], q=s["q"] / 1e18, via=s["to"][:10] + ":" + s["sel"]) for s in p["sw"]
                    if s["buy"] and s["have_tx"] and not s["bot"] and s["eoa"] not in botw and not s["eoa"].startswith(SENTINEL_PREFIX) and s["eoa"] not in OURS]
pickle.dump({"slice": name, "meta": {k: D[k] for k in ("a", "b", "ta", "tb")}, "pools": P, "botw": botw}, open(f"parsed_{name}.pkl", "wb"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"{name}: pools {len(P)}, with a bot buy {len(Ts)}; T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts)} max {max(Ts)}; "
      f"bot wallets {len(botw)}; missing swap txs to L+100 {sum(1 for p in P for s in p['sw'] if s['off'] <= 100 and not s['have_tx'])}; "
      f"pulled by L+200 {sum(1 for p in P if p['pull'] is not None)}")
print("  T buy size (ETH) p10/50/90:", [round(pct([p['Tq'] for p in P if p['Tq']], x), 4) for x in (.1, .5, .9)], "; bot buys per pool p50", pct([p["nbot"] for p in P], .5))
print("  T calldata length:", collections.Counter(p["Tinlen"] for p in P if p["Tinlen"]), "; swap 'sender' (router) of T:", collections.Counter(p["Trouter"] for p in P if p["Trouter"]))
print("  T histogram:", sorted(collections.Counter(Ts).items()))
print("  pulls (offset, sender, to:sel):", sorted((p["pull"], p["pull_eoa"][:10], p["pull_sel"]) for p in P if p["pull"] is not None))
print("  outside buys before T (or no T) with size >= 0.00003:", [(p["L"], o["off"], p["T"], o["eoa"][:10], round(o["q"], 6), o["via"], p["pull"]) for p in P for o in p["outside"]
       if o["q"] >= 0.00003 and (p["T"] is None or o["off"] < p["T"] or (o["off"] == p["T"] and o["ti"] < p["Tti"]))])
