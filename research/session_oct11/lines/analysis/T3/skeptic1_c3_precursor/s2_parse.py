"""Stage 2: per pool, swaps with their transactions; T = block offset of the bot's first buy (a buy whose tx goes to the bot router 0x1cbaf24d
with selector c1120e3d), its wallet, nonce, size, its deadline argument; later bot buys; pulls (ModifyLiquidity with negative delta);
outside buys before T (not the bot, not the sentinel 0xe71a69f4, >= 0.00003 ETH and dust). -> parsed_<tags>.pkl"""
import sys, json, pickle, collections
from lib import *
tags = sys.argv[1].split(",") if len(sys.argv) > 1 else ["old"]
kv_tx = KV("tx")
P = []
for tag in tags:
    D = json.load(open(f"pools_{tag}.json"))
    for p in D["pools"]:
        sw = []; ml = []
        for e in p["ev"]:
            t = kv_tx.d.get(e["tx"]) or {}
            base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(),
                    "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "nonce": int(t["nonce"], 16) if t.get("nonce") else None,
                    "have_tx": bool(t), "inp": t.get("input"), "psender": e.get("sender", "").lower()}
            if e["kind"] == "swap":
                a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
                r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
                r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
                sw.append(r)
            else:
                ml.append(dict(base, dL=sgn(W(e["data"], 2))))
        bots = [s for s in sw if s["bot"]]
        pulls = [m for m in ml if m["dL"] < 0]
        T = bots[0]["off"] if bots else None
        pre = [s for s in sw if bots and (s["bn"], s["li"]) < (bots[0]["bn"], bots[0]["li"])]
        q = dict(p); del q["ev"]
        q.update(tag=tag, sw=sw, ml=ml, T=T, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None, Ttx=bots[0]["tx"] if bots else None,
                 buyer=bots[0]["eoa"] if bots else None, buyer_nonce=bots[0]["nonce"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
                 Tinp=bots[0]["inp"] if bots else None, bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots),
                 pull=pulls[0]["off"] if pulls else None, pull_bn=pulls[0]["bn"] if pulls else None, pull_eoa=pulls[0]["eoa"] if pulls else None,
                 pull_sel=pulls[0]["sel"] if pulls else None,
                 pre=[dict(off=s["off"], bn=s["bn"], eoa=s["eoa"], to=s["to"], sel=s["sel"], buy=s["buy"], q=s["q"] / 1e18, sentinel=s["eoa"] == SENTINEL) for s in pre],
                 untouched_pre_missing=sum(1 for s in pre if not s["have_tx"]))
        P.append(q)
P.sort(key=lambda p: p["L"])
pickle.dump({"pools": P}, open(f"parsed_{'_'.join(tags)}.pkl", "wb"))
Ts = [p["T"] for p in P if p["T"] is not None]
print(f"slices {tags}: pools {len(P)}, with a bot buy {len(Ts)}; T p10/25/50/75/90 {[pct(Ts, x) for x in (.1, .25, .5, .75, .9)]} min {min(Ts)} max {max(Ts)}")
print("  pools without a bot buy to L+400:", sum(1 for p in P if p["T"] is None), "of which pulled:", sum(1 for p in P if p["T"] is None and p["pull"] is not None),
      "pull offsets:", sorted(p["pull"] for p in P if p["T"] is None and p["pull"] is not None)[:40])
print("  T histogram:", sorted(collections.Counter(Ts).items()))
print("  T's buyer nonce p10/50/90:", [pct([p["buyer_nonce"] for p in P if p["T"] is not None], x) for x in (.1, .5, .9)], "distinct buyers:", len(set(p["buyer"] for p in P if p["buyer"])))
print("  bot buy size (ETH) p10/50/90:", [round(pct([p["Tq"] for p in P if p["T"] is not None], x), 4) for x in (.1, .5, .9)])
print("  later bot buys per pool p50:", pct([p["nbot"] for p in P if p["T"] is not None], .5), "2nd buy - T p10/50/90:",
      [pct([p["bot2"] - p["T"] for p in P if p["bot2"] is not None], x) for x in (.1, .5, .9)])
pl = [p for p in P if p["T"] is not None and p["pull"] is not None]
print("  pools with T and pulled to L+400:", len(pl), "pull - T:", sorted(p["pull"] - p["T"] for p in pl))
pre_out = collections.Counter(); 
for p in P:
    if p["T"] is None: continue
    for s in p["pre"]:
        if s["sentinel"]: pre_out["sentinel"] += 1
        elif not s["buy"]: pre_out["sell before T"] += 1
        elif s["q"] >= 0.00003: pre_out["non-dust outside buy before T"] += 1
        else: pre_out["dust outside buy before T"] += 1
print("  swaps before T:", dict(pre_out), "missing txs among them:", sum(p["untouched_pre_missing"] for p in P))
hrs = collections.defaultdict(list)
for p in P:
    if p["T"] is not None: hrs[p["tag"] + ":" + str((p["L"] - P[0]["L"]) // 35000)].append(p["T"])
for k, v in sorted(hrs.items(), key=lambda kv: (kv[0].split(':')[0], int(kv[0].split(':')[1]))):
    print(f"   ~hour {k}: n {len(v)} T p10/50/90 {pct(v,.1)}/{pct(v,.5)}/{pct(v,.9)}")
