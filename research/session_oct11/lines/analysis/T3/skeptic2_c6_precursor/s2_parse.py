"""Stage 2: per 3.0 pool, its swaps with their transactions; T = the block of the bot's first buy (tx to the bot router 0x1cbaf24d,
selector c1120e3d); later bot buys; pulls (ModifyLiquidity with a negative delta); outside buys (not the bot router, not the sentinel)
with their size. The slice = pools launched in the most recent 2 hours (all after the finder's head 86158232). -> s2_parsed.pkl"""
import json, pickle, collections
from lib import *
D = json.load(open("s1_pools.json")); kv_tx = KV("tx")
FINDER_HEAD = 86158232
slice_start = D["head"] - int(2 * 3600 * D["bps"])
P = []
for p in D["pools"]:
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have_tx": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            r["outside"] = r["have_tx"] and r["to"] != BOT and r["eoa"] != SENTINEL and r["eoa"] != p["launcher"]
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]; pulls = [m for m in ml if m["dL"] < 0]; adds = [m for m in ml if m["dL"] > 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             Ttx=bots[0]["tx"] if bots else None, buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             bot_offs=[s["off"] for s in bots], pull=pulls[0]["off"] if pulls else None, pull_bn=pulls[0]["bn"] if pulls else None,
             L0=adds[0]["dL"] if adds else 0, in_slice=p["L"] >= slice_start and p["L"] <= D["head"] - 150, after_finder=p["L"] > FINDER_HEAD,
             pre_out=[(s["off"], s["q"] / 1e18, s["eoa"][:10]) for s in sw if s["outside"] and s["buy"] and (not bots or s["bn"] < bots[0]["bn"] or (s["bn"] == bots[0]["bn"] and s["ti"] < bots[0]["ti"]))])
    P.append(q)
pickle.dump({"head": D["head"], "head_ts": D["head_ts"], "bps": D["bps"], "slice_start": slice_start, "pools": P}, open("s2_parsed.pkl", "wb"))
S = [p for p in P if p["in_slice"]]
Ts = [p["T"] for p in S if p["T"] is not None]
print(f"head {D['head']}, slice start {slice_start} (2 h), finder's head {FINDER_HEAD}")
print(f"slice: 3.0 pools {len(S)} (all after the finder's head: {all(p['after_finder'] for p in S)}), with a bot buy {len(Ts)}, without {len(S) - len(Ts)}")
print(f"T offset p10/25/50/75/90 {[pct(Ts, x) for x in (.1, .25, .5, .75, .9)]} min {min(Ts)} max {max(Ts)}")
print("T distribution:", sorted(collections.Counter(Ts).items()))
best = max(range(15, 65), key=lambda k: sum(1 for t in Ts if abs(t - k) <= 1))
print(f"best fixed offset +-1: {best} covers {sum(1 for t in Ts if abs(t - best) <= 1)}/{len(Ts)}")
print("bot buy size at T (ETH) p10/50/90:", [round(pct([p['Tq'] for p in S if p['Tq']], x), 4) for x in (.1, .5, .9)])
print("bot buys per pool to L+400 p10/50/90:", [pct([len(p['bot_offs']) for p in S], x) for x in (.1, .5, .9)])
print("pulled (to L+400 or head):", sum(1 for p in S if p["pull"] is not None), [(p["pull"], p["T"]) for p in S if p["pull"] is not None])
print("pools with an outside buy before T (any size):", [(p["L"], p["T"], p["pre_out"]) for p in S if p["pre_out"]])
for p in S:
    if p["T"] is None: print("  no bot buy: L", p["L"], "pull", p["pull"], "swaps", [(s['off'], s['eoa'][:10], s['to'][:10], s['sel'], round(s['q']/1e18, 5), s['buy']) for s in p['sw'][:6]])
