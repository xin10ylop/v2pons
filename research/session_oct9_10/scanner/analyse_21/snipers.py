"""high-fee POSM pools (families 2-4 and the wider class): who buys at launch + 1..3 and how much LP fee the launchers collect from them"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer21 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta(); K = json.load(open(os.path.join(HERE, "keys.json"))); F = load_families()
deps = set(P[x]["launch_from"] for k in K[1:] for x in F[k]["pids"])
cls = [p["pid"] for p in P.values() if p["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and p["selector"] == "ac9650d8" and p["fee"] != 8388608 and p["fee"] >= 50000 and p["known"] == "none"]
E = load_events(set(cls)); out = {}
for name, pids in (("fam2-4 deployers", [x for x in cls if P[x]["launch_from"] in deps]), ("all POSM fee>=5%", cls)):
    early = collections.Counter(); early_pools = 0; fees_eth = 0; eth_in = 0; sel = collections.Counter()
    for pid in pids:
        pl = Pool21(P[pid], E.get(pid), T, M)
        e = [x for x in pl.buys() if x["bn"] - pl.b0 <= 3]
        if e: early_pools += 1
        for x in e: early[x["from"]] += 1; sel[x["sel"]] += 1
        for x in pl.buys():
            eth_in += x["eth"]; fees_eth += x["eth"] * x["fee"] / 1e6
    out[name] = {"pools": len(pids), "pools_with_buy_by_+3": early_pools, "buyers_by_+3": early.most_common(6), "selectors_by_+3": sel.most_common(4),
                 "eth_in_all_buys": eth_in / 1e18, "lp_fee_on_buys_eth": fees_eth / 1e18, "lp_fee_usd": fees_eth / 1e18 * USD_PER_ETH}
    print(name, out[name])
json.dump(out, open(os.path.join(HERE, "snipers.json"), "w"), indent=1)
