"""Stage 2: per 3.0 pool, the swaps with their transactions; T = offset of the bot's first buy (a buy whose tx calls 0x1cbaf24d with c1120e3d);
pulls (ModifyLiquidity with negative delta); outside buys (not the bot's router, not the sentinel 0xe71a69f4, not ours) and the pull lag after
each. Reaction table: the lag from an outside non-dust buy (>= 0.00003 ETH) to the first pull, split into buys before T and after T.
-> k2_parsed.pkl"""
import json, pickle, collections, os
from lib import *
os.chdir(HERE)
D = json.load(open("k1_pools.json")); kv_tx = KV("tx")
P = []
for p in D["pools"]:
    sw, ml = [], []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["who"] = ("bot" if r["to"] == BOT and r["sel"] == "c1120e3d" else "sentinel" if r["eoa"] == SENTINEL else
                        "ours" if r["eoa"] == OURS or r["to"] == RELAY else "outside")
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["who"] == "bot" and s["buy"]]
    pulls = [m for m in ml if m["dL"] < 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             Ttx=bots[0]["tx"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None, nbot=len(bots), bot2=bots[1]["off"] if len(bots) > 1 else None,
             pull=pulls[0]["off"] if pulls else None, pull_bn=pulls[0]["bn"] if pulls else None, pull_eoa=pulls[0]["eoa"] if pulls else None,
             pull_to=pulls[0]["to"] if pulls else None, pull_sel=pulls[0]["sel"] if pulls else None, missing=sum(1 for s in sw if not s["have"]))
    P.append(q)
pickle.dump({"head": D["head"], "head_ts": D["head_ts"], "bps": D["bps"], "pools": P}, open("k2_parsed.pkl", "wb"))
withT = [p for p in P if p["T"] is not None]
print(f"pools {len(P)}, with a bot buy {len(withT)}, missing txs {sum(p['missing'] for p in P)}; head {D['head']}")
Ts = [p["T"] for p in withT]
print(f"T offset p10/25/50/75/90 {[pct(Ts, x) for x in (.1, .25, .5, .75, .9)]} min {min(Ts)} max {max(Ts)}; bot buys per pool p50 {pct([p['nbot'] for p in withT], .5)}")
print("pulls:", sum(1 for p in P if p["pull"] is not None), "| puller to/sel:", collections.Counter((p["pull_to"][:10], p["pull_sel"]) for p in P if p["pull"] is not None).most_common(4))
print("no bot buy:", [(p["L"], p["span"], p["pull"]) for p in P if p["T"] is None])
# the reaction: outside non-dust buys and the first pull after them
print("\nREACTION: outside buys (not the bot's router, not the sentinel, not ours) and the first pull after the buy (lag in blocks)")
rows = []
for p in P:
    for s in p["sw"]:
        if s["who"] in ("outside", "ours") and s["buy"]:
            nxt = [m["bn"] for m in p["ml"] if m["dL"] < 0 and m["bn"] >= s["bn"]]
            lag = nxt[0] - s["bn"] if nxt else None
            when = "before T" if p["T"] is None or s["bn"] < p["Tbn"] or (s["bn"] == p["Tbn"] and s["ti"] < p["Tti"]) else "after T"
            rows.append(dict(L=p["L"], pid=p["pid"], off=s["off"], T=p["T"], eth=s["q"] / 1e18, eoa=s["eoa"], to=s["to"], who=s["who"], when=when, lag=lag,
                             span_left=p["L"] + p["span"] - s["bn"], dust=s["q"] < 3 * 10 ** 13))
for r in rows:
    print(f"  L {r['L']} {r['who']:7s} {r['eoa'][:10]} via {r['to'][:10]} {r['eth']:.6f} ETH at +{r['off']:<3d} T {r['T']!s:>4} {r['when']:8s} {'dust' if r['dust'] else '    '} "
          f"pull lag {r['lag']!s:>4} (blocks of history after the buy {r['span_left']})")
for when in ("before T", "after T"):
    nd = [r for r in rows if r["when"] == when and not r["dust"]]
    first = {}
    for r in nd:
        first.setdefault(r["pid"], r)
    lags = sorted(r["lag"] for r in first.values() if r["lag"] is not None)
    print(f"{when}: non-dust outside buys {len(nd)} in {len(first)} pools; first such buy per pool: pulled within 30 blocks {sum(1 for l in lags if l <= 30)}, "
          f"lags {lags}; min {lags[0] if lags else None} median {pct(lags, .5) if lags else None}")
pickle.dump(rows, open("k2_reaction_rows.pkl", "wb"))
