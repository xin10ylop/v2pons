"""control families (v2.433, operator A): the same descriptive numbers as the assigned families (first buy, pull, trap), for the record"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
out = {}
for lab in ("vbot-v2.433", "operator-A"):
    pids = [p for p, r in P.items() if r["known"] == lab]; E = load_events(set(pids))
    pls = [Pool(P[x], E.get(x), T, M) for x in pids]
    if lab == "vbot-v2.433":
        sb = [(pl, next((x for x in pl.buys() if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"), None)) for pl in pls]
    else:
        sb = [(pl, next((x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS), None)) for pl in pls]
    sb = [(pl, x) for pl, x in sb if x]
    pulled = [pl for pl in pls if pl.pull_bn is not None]
    out[lab] = {"count": len(pls), "per_day": round(len(pls) / WINDOW_DAYS, 1), "sched_frac": round(len(sb) / len(pls), 3),
                "sched_off_p10_50_90": q([x["bn"] - pl.b0 for pl, x in sb]), "sched_eth_p10_50_90": q([x["eth"] / 1e18 for pl, x in sb]),
                "sched_to": collections.Counter(x["to"] for pl, x in sb).most_common(2), "sched_n_from": len(set(x["from"] for pl, x in sb)),
                "pulled_frac": round(len(pulled) / len(pls), 3), "pull_off_p10_50_90": q([pl.pull_bn - pl.b0 for pl in pulled]),
                "pull_after_sched_p10_50_90": q([pl.pull_bn - x["bn"] for pl, x in sb if pl.pull_bn is not None]),
                "pull_by_launch_wallet": sum(1 for pl in pulled if pl.p["first_pull_from"] == pl.p["launch_from"])}
    print(lab, out[lab])
json.dump(out, open(os.path.join(HERE, "controls_extra.json"), "w"), indent=1)
