"""analyse_17 copy of analyse_15/calib.py (pricer common17). Calibration of the pricer against our own live relay trades: in every v2.433 (and operator-A) pool where the relay bought and sold
inside the 3,000-block window, compare the realised gross return (from the relay's own Swap events) with the replay's at the same buy
block B, sell block S and stake (the relay's swaps removed from the chain state, ours re-inserted at the end of B, sold at the head of S)."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common17 import *  # noqa

P = load_pools(); T = load_txs(); M = load_blocks_meta()
out = {}
for lab in ("vbot-v2.433", "operator-A"):
    pids = [p for p, r in P.items() if r["known"] == lab]
    E = load_events(set(pids))
    res = []
    for pid in pids:
        pool = Pool(P[pid], E.get(pid), T, M)
        rel = [x for x in pool.seq if x["relay"]]
        rb = [x for x in rel if x["buy"]]; rs = [x for x in rel if not x["buy"]]
        if len(rb) != 1 or len(rs) != 1: continue
        b, s = rb[0], rs[0]
        stake = b["eth"]; got = s["eth"]
        real = (got - stake) / stake
        sim = pool.trade(b["bn"], s["bn"], stake=stake)
        # the relay sells into the bot's buy in the SAME block (behind it): the replay's sell is at the head of S, so price it at S + 1 as well
        sim1 = pool.trade(b["bn"], s["bn"] + 1, stake=stake)
        same_block_after = any(x["bn"] == s["bn"] and x["li"] < s["li"] and not x["relay"] for x in pool.seq)
        res.append({"pid": pid, "B": b["bn"] - pool.b0, "S": s["bn"] - pool.b0, "stake": stake / 1e18, "real": real, "sim_S": sim.get("gross"),
                    "sim_S1": sim1.get("gross"), "exit": sim["exit"], "swaps_before_sell_in_S": same_block_after, "buy_ti_last": b["ti"]})
    ok = [r for r in res if r["sim_S"] is not None]
    # the matching replay: S if nothing precedes our sell in its block, else S + 1 (the swaps of S before our sell)
    d = [((r["sim_S1"] if r["swaps_before_sell_in_S"] else r["sim_S"]) - r["real"]) for r in ok if (r["sim_S1"] if r["swaps_before_sell_in_S"] else r["sim_S"]) is not None]
    out[lab] = {"n": len(res), "n_priced": len(ok), "real_mean": st.mean(r["real"] for r in ok) if ok else None,
                "sim_matched_mean": st.mean(((r["sim_S1"] if r["swaps_before_sell_in_S"] else r["sim_S"]) for r in ok)) if ok else None,
                "diff_p10_50_90": q(d, nd=6), "abs_diff_median": st.median(abs(x) for x in d) if d else None,
                "within_0.5pt": sum(1 for x in d if abs(x) < 0.005), "B_rel": collections.Counter(r["B"] for r in res).most_common(4),
                "worst": sorted(ok, key=lambda r: -abs(((r["sim_S1"] if r["swaps_before_sell_in_S"] else r["sim_S"]) or 0) - r["real"]))[:5]}
    print(lab, json.dumps({k: v for k, v in out[lab].items() if k != "worst"}, default=str))
    for w in out[lab]["worst"][:3]: print("   worst", w)
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1, default=str)
