"""Stage 2: per pool the swaps with their transactions; T = block offset of the bot's first buy (a buy whose tx calls 0x1cbaf24d with c1120e3d),
its wallet, nonce, size, calldata words; later bot buys; pulls (ModifyLiquidity with negative delta); outside buys before T and after.
-> parsed.pkl"""
import json, pickle, collections
from lib import *
D = json.load(open("pools.json")); kv_tx = KV("tx")
def words(inp): return [int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16) for i in range((len(inp) - 10) // 64)]
P = []
for p in D["pools"]:
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(),
                "sel": (t.get("input") or "")[2:10], "nonce": int(t["nonce"], 16) if t.get("nonce") else None, "have_tx": bool(t),
                "val": int(t["value"], 16) / 1e18 if t.get("value") else None}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            if r["bot"]: r["w"] = words(t["input"]); r["inlen"] = (len(t["input"]) - 2) // 2
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]
    T = bots[0]["off"] if bots else None
    q = dict(p); del q["ev"]
    out_pre = [s for s in sw if s["buy"] and not s["bot"] and T is not None and s["off"] <= T and s["eoa"] != SENTINEL]
    q.update(sw=sw, ml=ml, T=T, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None, Ttx=bots[0]["tx"] if bots else None,
             buyer=bots[0]["eoa"] if bots else None, buyer_nonce=bots[0]["nonce"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             Tw=bots[0]["w"] if bots else None, bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots),
             pull=pulls[0]["off"] if pulls else None, out_pre=[(s["off"], s["q"] / 1e18, s["eoa"]) for s in out_pre])
    P.append(q)
pickle.dump({"head": D["head"], "head_ts": D["head_ts"], "pools": P}, open("parsed.pkl", "wb"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"pools {len(P)}, with a bot buy {len(Ts)}, no bot buy {len(P)-len(Ts)} (spans of those: {[p['span'] for p in P if p['T'] is None]}, pulls {[p['pull'] for p in P if p['T'] is None]})")
print(f"T offsets p10/25/50/75/90 {[pct(Ts,x) for x in (.1,.25,.5,.75,.9)]} min {min(Ts)} max {max(Ts)}; sorted {sorted(Ts)}")
print(f"T size ETH: {sorted(round(p['Tq'],4) for p in P if p['T'] is not None)}")
b2 = [p['bot2'] - p['T'] for p in P if p['bot2'] is not None]; print(f"2nd bot buy - T p10/50/90 {pct(b2,.1)}/{pct(b2,.5)}/{pct(b2,.9)} n {len(b2)}; bot buys per pool p50 {pct([p['nbot'] for p in P if p['T'] is not None],.5)}")
print(f"pulled {sum(1 for p in P if p['pull'] is not None)} at {sorted((p['pull'], p['T']) for p in P if p['pull'] is not None)} (pull, T)")
print(f"missing txs (swaps to L+120): {sum(1 for p in P for s in p['sw'] if s['off'] <= 120 and not s['have_tx'])}")
print("outside (non-bot, non-sentinel) buys at or before T:", [(p['L'], p['T'], p['out_pre']) for p in P if p['out_pre']])
print("bot buy calldata lengths:", collections.Counter(p['Tw'] and len(p['Tw']) for p in P))
p0 = next(p for p in P if p['T'] is not None)
print("example bot buy words:", [hex(x) for x in p0['Tw']])
