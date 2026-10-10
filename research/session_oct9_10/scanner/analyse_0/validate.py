"""Validate the pool model against the chain: every buy's token output predicted by v4math.buy_out_int from the chain's own before-state
(previous swap's sqrtP, the effective start price for the first swap) and active liquidity, compared with the Swap event's a1."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import sys
FAMS = json.load(open(os.path.join(HERE, "families_in.json")))
P = load_pools(); T = load_txs(); M = load_blocks_meta()
out = {}
for f in FAMS:
    pids = load_families()[f["key"]]["pids"]
    E = load_events(set(pids))
    errs = []; first_errs = []; nr = collections.Counter(); seff = 0
    for pid in pids:
        pl = Pool(P[pid], E.get(pid), T, M)
        nr[pl.n_ranges] += 1
        if pl.s_eff != pl.sp0: seff += 1
        L = pl.L0
        for i, x in enumerate(pl.seq):
            if x["buy"] and L > 0:
                pred = v4math.buy_out_int(int(x["prev_sp"]), L, x["eth"], x["fee"])
                if x["a1"] > 0:
                    err = (pred - x["a1"]) / x["a1"]
                    errs.append(abs(err))
                    if i == 0: first_errs.append(abs(err))
            L = x["liq"]
    errs.sort(); first_errs.sort()
    out[f["key"]] = {"n_buys": len(errs), "median_abs_err": errs[len(errs) // 2] if errs else None, "p99_abs_err": errs[int(.99 * (len(errs) - 1))] if errs else None,
                     "share_over_1e-6": sum(1 for e in errs if e > 1e-6) / max(1, len(errs)), "first_swap_median_err": first_errs[len(first_errs) // 2] if first_errs else None,
                     "first_swap_over_1e-6": sum(1 for e in first_errs if e > 1e-6), "n_first": len(first_errs), "ranges_in_live_tx": dict(nr), "start_below_sp0": seff}
    print(f["key"], out[f["key"]], flush=True)
json.dump(out, open(os.path.join(HERE, "validate.json"), "w"), indent=1)
