"""Skeptic 1, stage 2: per 3.0 pool of the oldest slice: T (block offset of the bot's first buy = a buy whose tx calls 0x1cbaf24d with
c1120e3d), its block/tx index/wallet/size, later bot buys, every other buy before the pull (who, size, offset, to+selector), pulls
(ModifyLiquidity with negative delta: offset, tx, sender/to/selector) -> parsed.pkl; prints the line's shape by hour."""
import json, pickle, collections, statistics as st
from lib import *
import sys
TAG = ("_" + sys.argv[1]) if len(sys.argv) > 1 else ""
D = json.load(open(f"pools{TAG}.json")); kv_tx = KV("tx"); kb = KV("blkts")
NEW30 = 1791692539   # 04:22:19 UTC, REPORT_R's late-bot regime start
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
             Ttx=bots[0]["tx"] if bots else None, buyer=bots[0]["eoa"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots), pull=pulls[0]["off"] if pulls else None, pullbn=pulls[0]["bn"] if pulls else None,
             pull_to=pulls[0]["to"] + ":" + pulls[0]["sel"] if pulls else None)
    P.append(q)
# timestamps of launch blocks (for the regime split)
need = [p["L"] for p in P if str(p["L"]) not in kb.d]
for i in range(0, len(need), 100):
    ch = need[i:i + 100]; res = batch([("eth_getBlockByNumber", [hex(n), False]) for n in ch], 25)
    for n, b in zip(ch, res):
        if b: kb.put(str(n), int(b["timestamp"], 16))
    kb.flush()
for p in P: p["ts"] = kb.d.get(str(p["L"]))
pickle.dump({"A": D["A"], "B": D["B"], "pools": P}, open(f"parsed{TAG}.pkl", "wb"))
print(f"3.0 pools {len(P)}; with a bot buy {sum(1 for p in P if p['T'] is not None)}; missing swap txs (to L+150) {sum(1 for p in P for s in p['sw'] if not s['have_tx'] and s['off'] <= 150)}")
print("pull senders (to:selector):", collections.Counter(p["pull_to"] for p in P if p["pull_to"]).most_common(5))
byh = collections.defaultdict(list)
for p in P: byh[time.strftime("%H", time.gmtime(p["ts"]))].append(p)
print(f"\n{'hour':>4} {'pools':>5} {'withT':>5} {'T p10/50/90':>12} {'Tmin':>4} {'Tmax':>4} {'2nd-T p50':>9} {'nbot p50':>8} {'Tq p50':>7} {'pulled':>6} {'pull p50':>8}")
for h in sorted(byh):
    G = byh[h]; Ts = [p["T"] for p in G if p["T"] is not None]; b2 = [p["bot2"] - p["T"] for p in G if p["bot2"] is not None]
    pl = [p["pull"] for p in G if p["pull"] is not None]
    print(f"{h:>4} {len(G):5d} {len(Ts):5d} {str((pct(Ts,.1),pct(Ts,.5),pct(Ts,.9))):>12} {min(Ts) if Ts else '-':>4} {max(Ts) if Ts else '-':>4} {pct(b2,.5)!s:>9} "
          f"{pct([p['nbot'] for p in G],.5)!s:>8} {pct([p['Tq'] for p in G if p['Tq']],.5) or 0:7.3f} {len(pl):6d} {pct(pl,.5)!s:>8}")
for lab, G in (("before 04:22", [p for p in P if p["ts"] < NEW30]), ("from 04:22", [p for p in P if p["ts"] >= NEW30])):
    Ts = [p["T"] for p in G if p["T"] is not None]
    print(f"{lab}: pools {len(G)}, with T {len(Ts)}, T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)}, histogram " + str(sorted(collections.Counter(Ts).items())))
