"""Stage 5: the operator's reaction to an outside buy that lands BEFORE the bot's first buy (the situation of a front), re-measured from the
chain on the current-regime 3.0 pools (T at L+18..+60, from 10-11 04:22 UTC): every slice parsed here (cur = 04:22..09:38, recent = 09:38..now).
Outside buy = a buy whose tx is not the bot's (to 0x1cbaf24d c1120e3d), not the sentinel 0xe71a69f4, >= 0.00003 ETH (non-dust), landing before
the bot's first buy (or in a pool where the bot never bought). Lag = first pull (ModifyLiquidity with negative delta) block - that buy's block.
Also: did the bot still buy; buys after T for comparison (to L+120, where every swap tx is fetched)."""
import pickle, collections, sys
from lib import *
CUR0 = 85553521
sets = sys.argv[1].split(",") if len(sys.argv) > 1 else ["mid", "recent"]
P = []
for s in sets:
    P += [p for p in pickle.load(open(f"parsed_{s}.pkl", "rb"))["pools"] if p["L"] >= CUR0]
P.sort(key=lambda p: p["L"])
print(f"current-regime pools: {len(P)} (L {P[0]['L']}..{P[-1]['L']}), with a bot buy {sum(1 for p in P if p['T'] is not None)}, pulled to L+400 {sum(1 for p in P if p['pull'] is not None)}")
pre = []; post = []; nodust = collections.Counter()
for p in P:
    Tkey = None
    bots = [s for s in p["sw"] if s["bot"]]
    if bots: Tkey = (bots[0]["bn"], bots[0]["li"])
    pulls = [m for m in p["ml"] if m["dL"] < 0]
    seen = set()
    for s in p["sw"]:
        if not s["have_tx"] or s["bot"] or s["eoa"] == SENTINEL or not s["buy"]: continue
        if s["q"] < 3 * 10 ** 13: nodust[("dust", "pre" if Tkey is None or (s["bn"], s["li"]) < Tkey else "post")] += 1; continue
        if s["eoa"] in seen: continue
        seen.add(s["eoa"])
        pl = [m for m in pulls if (m["bn"], m["li"]) > (s["bn"], s["li"])]
        lag = pl[0]["bn"] - s["bn"] if pl else None
        row = dict(L=p["L"], off=s["off"], eoa=s["eoa"], to=s["to"], sel=s["sel"], q=s["q"] / 1e18, T=p["T"], lag=lag, pull_off=pl[0]["off"] if pl else None,
                   bot_bought_after=bool(bots) and (bots[0]["bn"], bots[0]["li"]) > (s["bn"], s["li"]), span=p.get("span"))
        (pre if Tkey is None or (s["bn"], s["li"]) < Tkey else post).append(row)
def show(rows, lab):
    lags = [r["lag"] for r in rows if r["lag"] is not None]
    print(f"\n{lab}: {len(rows)} (pool, wallet) cases in {len(set(r['L'] for r in rows))} pools; pulled after it to L+400: {len(lags)}; "
          f"lag (blocks) sorted: {sorted(lags)}")
    if lags: print(f"   lag min {min(lags)} p25 {pct(lags,.25)} median {pct(lags,.5)} p75 {pct(lags,.75)} max {max(lags)}; within 14 blocks: {sum(1 for x in lags if x <= 14)} of {len(rows)}")
    by = collections.Counter(r["eoa"] for r in rows)
    print("   by wallet:", [(w[:10], n) for w, n in by.most_common(8)])
    for r in rows[:60]:
        print(f"   L {r['L']} buy at +{r['off']} {r['eoa'][:10]} via {r['to'][:10]}:{r['sel']} {r['q']:.5f} ETH | T {r['T']} bot bought after it: {r['bot_bought_after']} | pull +{r['pull_off']} lag {r['lag']}")
show(pre, "PRE-T outside non-dust buys (before the bot's first buy, or the bot never bought)")
show(post, "POST-T outside non-dust buys (to L+120)")
print("\ndust (< 0.00003 ETH) buys:", dict(nodust))
pickle.dump({"pre": pre, "post": post}, open("s5_reaction.pkl", "wb"))
