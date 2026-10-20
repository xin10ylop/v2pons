"""Follow on the C-1 line (and others): trigger = the first buy >= X ETH by anyone (events), or the first real buy via the operator
router 0xd6d35b56; buy at trigger + d (d = 1, 2, 3), sell at a + H (fixed) or engine-style take-profit (sell the block after a buy behind
ours lifts us >= TP, else at a + H). Per day. q = 0.0058 / 0.002."""
from cands import *
from replay import *
from tp_grid import tp_replay
rows = rows_nonvbot(); E = load_ev()
OPR = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"


def trig_off(r, P, X):
    for w in P["sw"]:
        if w["buy"] and to_eth(r, w["q"]) >= X: return w["bn"] - P["lb"]
    return None


RES = {}
for name in ("C1_eth", "C1_weth", "odd2_1444", "564f_weth_hook", "a98b_hook"):
    rs = [r for r in rows if CANDS[name](r)]
    Ps = {r["pool"]: prep(r, E[r["pool"]]) for r in rs}; rs = [r for r in rs if Ps[r["pool"]]["L0"] > 0]
    n = len(rs); print(f"\n===== {name} n={n} ({n/7:.1f}/day)")
    trigs = {f"buy>={X}": {r["pool"]: trig_off(r, Ps[r["pool"]], X) for r in rs} for X in (0.005, 0.02, 0.05)}
    trigs["frb via 0xd6d35b56"] = {r["pool"]: (r["frb"]["off"] if r.get("frb") and r["frb"]["to"] == OPR else None) for r in rs}
    for tn, T in trigs.items():
        have = [r for r in rs if T[r["pool"]] is not None and T[r["pool"]] <= 600]
        if len(have) < 15: continue
        for d in (1, 2, 3):
            for ex in ("H20", "H40", "H60", "H100", "tp0.05/H60", "tp0.10/H100", "tp0.20/H100"):
                for q in (0.0058, 0.002):
                    res = []; byd = C.defaultdict(list)
                    for r in have:
                        a = T[r["pool"]] + d
                        if ex.startswith("H"): x = replay(r, Ps[r["pool"]], a, a + int(ex[1:]), q)
                        else:
                            tp, H = ex.split("/"); x = tp_replay(r, Ps[r["pool"]], a, int(H[1:]), float(tp[2:]), q)
                        res.append(x)
                        if x: byd[day_of(r)].append(x)
                    st = stats(res, n / 7, len(have) / n); st["tradable_share"] = round(len(have) / n, 3); st["by_day"] = {dd: stats(byd[dd]) for dd in range(7)}
                    RES[f"{name}|{tn}|d{d}|{ex}|q{q}"] = st
                    if q == 0.0058 and d == 2 or (q == 0.0058 and ex in ("H60",)):
                        dd = " ".join(f"{st['by_day'][k].get('mean', 0):+.3f}" if st['by_day'][k].get('n') else "-" for k in range(7))
                        print(f"  {tn:20s} d{d} {ex:12s} n={st['n']:4d} trad={st['tradable_share']:.2f} mean={st['mean']:+.4f} med={st['median']:+.4f} win={st['win']:.2f} worst={st['worst']:+.2f} pulled={st['pulled']:.3f} $/tr={st['mean_usd']:+.3f} $/day={st['usd_day']:+.1f} | {dd}")
json.dump(RES, open(os.path.join(OUT, "follow_grid.json"), "w"), indent=0, default=str)
