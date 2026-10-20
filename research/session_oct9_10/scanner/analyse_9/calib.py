import sys, json, collections, statistics as st
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
v24 = [k for k, f in F.items() if f["known"] == "vbot-v2.433"]
opa = [k for k, f in F.items() if f["known"] == "operator-A"]
print("v2.433 keys", v24, sum(F[k]["count"] for k in v24)); print("opA keys", len(opa), sum(F[k]["count"] for k in opa))
pv = [pid for k in v24 for pid in F[k]["pids"] if P[pid]["known"] == "vbot-v2.433"]
pa = [pid for k in opa for pid in F[k]["pids"] if P[pid]["known"] == "operator-A"]
E = load_events(set(pv) | set(pa))
out = {}
# --- v2.433 front: buy at +1 (end of block), sell at the head of the block after the bot's first router buy (or +20)
pools = [Pool(P[pid], E.get(pid), T, M) for pid in pv]
isbot = lambda x: x["to"] == VBOT_ROUTER
fr = [pl.front(isbot, minout=vbot_minout) for pl in pools]
out["v2433_front_botbuy"] = summarize(fr)
gen = [pl.front(lambda x: x["eth"] >= MIN_REAL, minout=vbot_minout) for pl in pools]
out["v2433_front_first_real_buy"] = summarize(gen)
fo = [pl.follow(minout=vbot_minout) for pl in pools]
out["v2433_follow"] = summarize(fo)
# where's the bot buy: within first-8 tx data?
nb = collections.Counter(r["sched_rel"] is not None for r in fr)
out["v2433_bot_buy_found"] = dict(nb)
out["v2433_sched_rel_p10_50_90"] = q([r["sched_rel"] for r in fr])
# live-window subset: Oct 10 09:07-11:40 UTC (our relay trading) -> compare with the live +13.97%
B = load_blocks()
import calendar
t0 = calendar.timegm((2026, 10, 10, 9, 7, 0)); t1 = calendar.timegm((2026, 10, 10, 11, 40, 0))
live = [r for pl, r in zip(pools, fr) if t0 <= pl.p["launch_ts"] <= t1]
out["v2433_front_live_window"] = summarize(live)
relay_pools = [pl for pl in pools if any(x["relay"] for x in pl.seq)]
out["v2433_pools_with_our_relay"] = len(relay_pools)
# capacity of the bot's first buy (decoded minOut)
caps = []
for pl in pools:
    fb = next((x for x in pl.buys() if isbot(x)), None)
    if fb and vbot_minout(fb): caps.append(capacity(pl, fb, vbot_minout(fb)))
out["v2433_capacity"] = {"n": len(caps), "total_eth_p10_50_90": q([c["total_eth"] for c in caps]), "extra_eth_p10_50_90": q([c["extra_eth"] for c in caps]),
                         "minout_over_launch_quote_p10_50_90": q([c["minout_over_launch_quote"] for c in caps])}
# --- operator A
pa_pools = [Pool(P[pid], E.get(pid), T, M) for pid in pa]
out["opA_follow"] = summarize([pl.follow() for pl in pa_pools])
out["opA_front_first_real_buy"] = summarize([pl.front(lambda x: x["eth"] >= MIN_REAL) for pl in pa_pools])
print(json.dumps(out, indent=1))
json.dump(out, open("calib.json", "w"), indent=1)
