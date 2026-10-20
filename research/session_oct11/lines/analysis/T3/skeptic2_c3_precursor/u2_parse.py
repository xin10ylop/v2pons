"""Stage 2: per 3.0 pool, swaps with their transactions; T = offset of the bot's first buy (a buy whose tx calls 0x1cbaf24d with c1120e3d),
its buyer wallet, size, minOut (word 4) and deadline (word 6); pulls (ModifyLiquidity with negative delta). Labels each pool:
  finder = used by the finder (its 200 pools with T, ../precursor/parsed.pkl - read only for the pid list),
  recent2h = launched at or after block 86133015 (2 h before the first run's head, 23:01 UTC; later runs add newer pools).
The test slice = recent2h pools with T that the finder did not use. -> u2_parsed.pkl"""
import json, pickle, collections, os
from lib import *
os.chdir(HERE)
D = json.load(open("u1_pools.json")); kv_tx = KV("tx")
FP = pickle.load(open(os.path.join(HERE, "..", "precursor", "parsed.pkl"), "rb"))
finder = {p["pid"].lower() for p in FP["pools"] if p["line"] == "3.0" and p["T"] is not None}
finder_all = {p["pid"].lower() for p in FP["pools"] if p["line"] == "3.0"}
cut2h = int(os.environ.get("CUT", "86133015"))   # fixed at the first run: head 86202613 (23:01 UTC) - 2 h; later runs add the newer pools to the slice
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
P = []
for p in D["pools"]:
    sw, ml = [], []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "have": bool(t), "nonce": int(t["nonce"], 16) if t.get("nonce") else None}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["who"] = ("bot" if r["to"] == BOT and r["sel"] == "c1120e3d" else "sentinel" if r["eoa"] == SENTINEL else
                        "ours" if r["eoa"] == OURS or r["to"] == RELAY else "outside")
            if r["who"] == "bot" and len(t.get("input", "")) >= 10 + 64 * 7:
                r["minout"] = word(t["input"], 4); r["deadline"] = word(t["input"], 6)
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["who"] == "bot" and s["buy"]]
    pulls = [m for m in ml if m["dL"] < 0]; adds = [m for m in ml if m["dL"] > 0]
    q = {k: v for k, v in p.items() if k != "ev"}
    q.update(sw=sw, ml=ml, L0=adds[0]["dL"] if adds else 0, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None,
             Tti=bots[0]["ti"] if bots else None, Ttx=bots[0]["tx"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             buyer=bots[0]["eoa"] if bots else None, buyer_nonce=bots[0]["nonce"] if bots else None, nbot=len(bots),
             bot2=bots[1]["off"] if len(bots) > 1 else None, pull=pulls[0]["off"] if pulls else None, pull_bn=pulls[0]["bn"] if pulls else None,
             pull_eoa=pulls[0]["eoa"] if pulls else None, pull_to=pulls[0]["to"] if pulls else None, pull_sel=pulls[0]["sel"] if pulls else None,
             missing=sum(1 for s in sw if not s["have"]), finder=p["pid"] in finder, finder_any=p["pid"] in finder_all, recent2h=p["L"] >= cut2h)
    P.append(q)
pickle.dump({"head": D["head"], "head_ts": D["head_ts"], "bps": D["bps"], "cut2h": cut2h, "pools": P}, open("u2_parsed.pkl", "wb"))
withT = [p for p in P if p["T"] is not None]
print(f"head {D['head']} ({utc(D['head_ts'])} UTC); pools {len(P)} (L {P[0]['L']}..{P[-1]['L']}), with a bot buy {len(withT)}, missing txs {sum(p['missing'] for p in P)}")
print(f"finder's 200 pools with T: L {min(p['L'] for p in FP['pools'] if p['pid'].lower() in finder)}..{max(p['L'] for p in FP['pools'] if p['pid'].lower() in finder)}; finder head {FP['head']}")
print(f"of mine: in the finder's T-set {sum(p['finder'] for p in P)}, in the finder's launch list {sum(p['finder_any'] for p in P)}")
R2 = [p for p in P if p["recent2h"]]
print(f"recent 2 h (L >= {cut2h}): launches {len(R2)}, with T {sum(1 for p in R2 if p['T'] is not None)}, of them used by the finder {sum(1 for p in R2 if p['finder'])}; "
      f"TEST SLICE (recent 2 h, with T, not the finder's): {sum(1 for p in R2 if p['T'] is not None and not p['finder'])}")
for name, G in (("all 7 h", withT), ("test slice", [p for p in R2 if p["T"] is not None and not p["finder"]])):
    Ts = [p["T"] for p in G]
    print(f"{name}: T p10/25/50/75/90 {[pct(Ts, x) for x in (.1, .25, .5, .75, .9)]} min {min(Ts)} max {max(Ts)}; T ETH p50 {pct([p['Tq'] for p in G], .5):.4f}; "
          f"bot buys/pool p50 {pct([p['nbot'] for p in G], .5)}; 2nd buy at T+{pct([p['bot2'] - p['T'] for p in G if p['bot2']], .5)}; pulled {sum(1 for p in G if p['pull'] is not None)}")
print("no bot buy (L, span, pull, outside buys before pull):", [(p["L"], p["span"], p["pull"], [(s["off"], round(s["q"] / 1e18, 5), s["eoa"][:10]) for s in p["sw"] if s["who"] in ("outside", "ours") and s["buy"]][:3]) for p in P if p["T"] is None])
print("puller to/sel:", collections.Counter((p["pull_to"][:10], p["pull_sel"]) for p in P if p["pull"] is not None).most_common(4))
print("bot buyer wallets:", len({p["buyer"] for p in withT}), "| first-buy deadline - ? (see u4)")
