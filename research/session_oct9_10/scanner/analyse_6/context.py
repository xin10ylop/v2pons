"""Context for the four families: the wider 7fde822e launcher type (all contracts, all deployers) and the 0x0000ffff contract's other
calls; does ANY pool of these launcher types get a buy >= 0.0002 ETH or a pull within 3,000 blocks?"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools(); LF = load_loose_families(); TF = load_to_families()
sel = [pid for pid, p in P.items() if p["selector"] == "7fde822e"]
ff = [pid for pid, p in P.items() if p["launch_to"] == "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0"]
E = load_events(set(sel) | set(ff)); T = load_txs()
out = {}
for name, group in (("7fde822e_all", sel), ("0x0000ffff_all", ff)):
    deps = collections.Counter(P[p]["launch_from"] for p in group); tos = collections.Counter(P[p]["launch_to"] for p in group)
    fees = collections.Counter((P[p]["fee"], P[p]["tick_spacing"], P[p]["hooks_zero"]) for p in group)
    vals = collections.Counter(P[p]["launch_value_eth"] for p in group)
    real_buy_pools = []; pull_pools = []; buyers = collections.Counter(); any_nondust = 0
    for pid in group:
        e = E.get(pid) or {"swaps": [], "pulls": []}
        lt = P[pid]["launch_tx"]
        bs = [s for s in e["swaps"] if s["a0"] < 0 and s["tx"] != lt]
        nd = [s for s in bs if not (T.get(s["tx"]) and T[s["tx"]]["from"] == DUST)]
        if nd: any_nondust += 1
        rb = [s for s in bs if -s["a0"] >= MIN_REAL]
        if rb:
            t = T.get(rb[0]["tx"])
            real_buy_pools.append({"pid": pid, "dep": P[pid]["launch_from"], "to": P[pid]["launch_to"], "rel": rb[0]["bn"] - P[pid]["launch_block"], "eth": -rb[0]["a0"] / 1e18,
                                   "from": t and t["from"], "via": t and t["to"], "n_real": len(rb), "pull": P[pid]["first_pull_rel"]})
        if e["pulls"]: pull_pools.append({"pid": pid, "rel": e["pulls"][0]["bn"] - P[pid]["launch_block"], "dep": P[pid]["launch_from"]})
        for s in nd:
            t = T.get(s["tx"]); buyers[(t and t["from"], t and t["to"])] += 1
    out[name] = {"pools": len(group), "deployers": deps.most_common(10), "n_deployers": len(deps), "launch_to": tos.most_common(30), "n_launch_to": len(tos),
                 "fee_ts_hookszero": [[list(k), v] for k, v in fees.most_common()], "values": vals.most_common(5),
                 "pools_with_nondust_buy": any_nondust, "pools_with_real_buy": len(real_buy_pools), "real_buy_examples": real_buy_pools[:40],
                 "pools_with_pull": len(pull_pools), "pull_examples": pull_pools[:20], "nondust_buyers_top": [[list(k), v] for k, v in buyers.most_common(15)]}
    # per deployer: launch cadence
    cad = {}
    for d, n in deps.most_common(10):
        bl = sorted(P[p]["launch_block"] for p in group if P[p]["launch_from"] == d)
        gaps = [b - a for a, b in zip(bl, bl[1:])]
        cad[d] = {"n": n, "gap_blocks_p10_50_90": pct(gaps), "first": bl[0], "last": bl[-1], "nonces": [min(P[p]["launch_nonce"] for p in group if P[p]["launch_from"] == d), max(P[p]["launch_nonce"] for p in group if P[p]["launch_from"] == d)]}
    out[name]["cadence"] = cad
json.dump(out, open(os.path.join(HERE, "context.json"), "w"), indent=1, default=str)
for k, v in out.items():
    print("=====", k)
    for a, b in v.items(): print(" ", a, json.dumps(b, default=str)[:900])
