"""Stage 2: per 3.0 pool: swaps with their transactions; T = the block of the bot's first buy (a buy whose tx calls the bot router 0x1cbaf24d
with c1120e3d), its tx index, wallet, size; later bot buys; pulls (ModifyLiquidity with a negative delta); outside buys (not the bot router,
not the sentinel 0xe71a69f4) with size, block and the pull lag after them. Regime: the 3.0 line's late-bot regime from 04:22:19 UTC Oct 11
(REPORT_R), decided by the launch block's time. -> parsed.pkl"""
import json, pickle, collections
from lib import *
D = json.load(open("pools.json")); kv_tx = KV("tx")
NEW30 = 1791692539
bps = (D["end"] - D["start"]) / (D["t1"] - D["t0"])
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
P = []
for p in D["launches"]:
    if p["line"] != "3.0": continue
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(),
                "sel": (t.get("input") or "")[2:10], "have_tx": bool(t), "input": t.get("input") if e["kind"] == "swap" and (t.get("to") or "").lower() == BOT else None}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]
    q = {k: v for k, v in p.items() if k not in ("ev",)}
    q["regime"] = "new" if D["t0"] + (p["L"] - D["start"]) / bps >= NEW30 else "old"
    pull = pulls[0] if pulls else None
    outs = [s for s in sw if s["buy"] and not s["bot"] and s["eoa"] != SENTINEL and s["have_tx"]]
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None, Ttx=bots[0]["tx"] if bots else None,
             Tinput=bots[0]["input"] if bots else None, nbot=len(bots), bot2=bots[1]["off"] if len(bots) > 1 else None,
             pull=pull["off"] if pull else None, pullbn=pull["bn"] if pull else None, pull_to=pull["to"] if pull else None, pull_sel=pull["sel"] if pull else None,
             outs=[{"off": s["off"], "bn": s["bn"], "ti": s["ti"], "q": s["q"] / 1e18, "eoa": s["eoa"], "to": s["to"], "sel": s["sel"]} for s in outs],
             missing=sum(1 for s in sw if s["bn"] <= p["L"] + 120 and not s["have_tx"]))
    P.append(q)
pickle.dump({"start": D["start"], "end": D["end"], "t0": D["t0"], "t1": D["t1"], "bps": bps, "pools": P}, open("parsed.pkl", "wb"))
for reg in ("old", "new"):
    G = [p for p in P if p["regime"] == reg]; Ts = [p["T"] for p in G if p["T"] is not None]
    print(f"regime {reg}: 3.0 pools {len(G)}, L {min(p['L'] for p in G)}..{max(p['L'] for p in G)}, with a bot buy {len(Ts)}, T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} "
          f"min {min(Ts)} max {max(Ts)}; missing txs {sum(p['missing'] for p in G)}; pulled {sum(1 for p in G if p['pull'] is not None)}; "
          f"pulled before T {sum(1 for p in G if p['pull'] is not None and (p['T'] is None or p['pull'] < p['T']))}; bot buys per pool p50 {pct([p['nbot'] for p in G], .5)}; "
          f"2nd buy - T p50 {pct([p['bot2'] - p['T'] for p in G if p['bot2'] is not None], .5)}")
    print("   T histogram:", sorted(collections.Counter(Ts).items()))
print("pull calls:", collections.Counter((p["pull_to"][:10], p["pull_sel"]) for p in P if p["pull"] is not None).most_common(5))
