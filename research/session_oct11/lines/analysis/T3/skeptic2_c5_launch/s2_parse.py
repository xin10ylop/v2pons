"""Stage 2: per 3.0 pool of the slice: swaps with their txs, T = the block of the bot's first buy (a buy whose tx calls the bot router 0x1cbaf24d
with c1120e3d), the bot's later buys, pulls (ModifyLiquidity with negative delta), outside buys (not the bot router, not the sentinel 0xe71a69f4,
not ours) with their size and the next pull's lag -> s2_parsed.json."""
import json, collections, statistics as st
from lib import *
S = json.load(open("s1_slice.json")); TX = S["txs"]
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
P = []; botw = collections.Counter()
for p in S["pools"]:
    sw = []; ml = []
    for e in p["ev"]:
        t = TX.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have_tx": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            r["minout"] = word(t["input"], 4) if r["bot"] and len(t.get("input", "")) >= 10 + 64 * 5 else None
            sw.append(r)
        else:
            ml.append(dict(base, lo=sgn(W(e["data"], 0)), hi=sgn(W(e["data"], 1)), dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]
    for w in {s["eoa"] for s in bots}: botw[w] += 1
    adds = [m for m in ml if m["dL"] > 0]; pulls = [m for m in ml if m["dL"] < 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, L0=adds[0]["dL"] if adds else 0, lo=adds[0]["lo"] if adds else None, hi=adds[0]["hi"] if adds else None,
             T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots), pull=pulls[0]["off"] if pulls else None, pullbn=pulls[0]["bn"] if pulls else None,
             missing=sum(1 for s in sw if not s["have_tx"]))
    P.append(q)
for p in P:
    for s in p["sw"]:
        s["who"] = ("bot" if s["bot"] else "botsell" if (not s["buy"] and s["eoa"] in botw) else "sentinel" if s["eoa"] == SENTINEL
                    else "ours" if (s["eoa"] == OURS or s["to"] == RELAY) else "w")
    p["outside"] = [dict(off=s["off"], bn=s["bn"], q=s["q"] / 1e18, eoa=s["eoa"], to=s["to"], preT=(p["T"] is None or s["bn"] < p["Tbn"] or (s["bn"] == p["Tbn"] and s["ti"] < p["Tti"])),
                         lag=(p["pull"] - s["off"]) if p["pull"] is not None and p["pull"] >= s["off"] else None)
                    for s in p["sw"] if s["buy"] and s["who"] in ("w", "ours") and s["q"] >= 3 * 10 ** 13]
json.dump({"start": S["start"], "head": S["head"], "ts_start": S["ts_start"], "ts_head": S["ts_head"], "pools": P, "botw": sorted(botw)}, open("s2_parsed.json", "w"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"3.0 pools {len(P)}; with a bot buy {len(Ts)}; T-L p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts)} max {max(Ts)}; "
      f"bot wallets {len(botw)}; swaps to L+400 without tx {sum(p['missing'] for p in P)}")
print("T-L histogram:", sorted(collections.Counter(Ts).items()))
print("first bot buy size ETH p10/50/90:", [round(x, 4) for x in (pct([p['Tq'] for p in P if p['T'] is not None], f) for f in (.1, .5, .9))])
print("bot buys per pool (to L+400):", sorted(collections.Counter(p["nbot"] for p in P).items()), "2nd bot buy - T p10/50/90:",
      [pct([p["bot2"] - p["T"] for p in P if p["bot2"] is not None], f) for f in (.1, .5, .9)])
print("pulled within L+400:", sum(1 for p in P if p["pull"] is not None), "offsets:", sorted(p["pull"] for p in P if p["pull"] is not None))
print("pools without T:", [(p["pid"][:10], p["L"], p["span"], p["pull"]) for p in P if p["T"] is None])
print("\noutside buys >= 0.00003 ETH (not the bot router, not the sentinel):")
for p in P:
    for o in p["outside"]:
        print(f"  pool {p['pid'][:10]} L {p['L']} T {p['T']} pull {p['pull']} | buy {o['q']:.6f} at +{o['off']} {'PRE-T' if o['preT'] else 'post-T'} from {o['eoa'][:10]} via {o['to'][:10]} -> pull lag {o['lag']}")
pre = [o["lag"] for p in P for o in p["outside"] if o["preT"]]; post = [o["lag"] for p in P for o in p["outside"] if not o["preT"]]
print("pre-T lags:", sorted(x for x in pre if x is not None), "unpulled:", sum(1 for x in pre if x is None))
print("post-T lags:", sorted(x for x in post if x is not None), "unpulled:", sum(1 for x in post if x is None))
