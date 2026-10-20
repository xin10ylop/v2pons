"""Expected return of the v2.433 rule if the operator treats our buy like the other outsiders' buys >= 0.0002 ETH (25 of 26 pulled within
15 blocks; lag = the empirical lags of all outsider first-buys followed by a pull within 15 blocks, v2.433 census). Per pool: the rule's
trade from the cheap pricer (detail.detail: B = buy block, send, ret); P(loss) = r x P(lag <= S - B), S = send + 1 (the sell's landing;
a pull in the same block counts as first). Entry K = 2..8 (fire at b0+K, buy lands at K+1), TP 5% H 19 and TP 1% H 19."""
import sys, os, pickle, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim, detail
LAGS = json.load(open("chk/react_all.json"))["v2.433"]["lags"]
L = np.array(LAGS)
def p_le(d): return float((L <= d).mean())
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
pools = [p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p] + [p for p in FP.values() if "v2.433" in p["fam"]]
print("pools", len(pools), "lags n", len(L), "P(lag<=d) d=2..10:", [round(p_le(d), 3) for d in range(2, 11)])
out = {}
for tp_i, tp in ((3, "TP5"), (0, "TP1")):
    for K in range(2, 9):
        e = sim.KS.index(K)
        for s in (0, 1):
            rows = [d for p in pools for d in [detail.detail(p, e, s, tp_i, sim.HS.index(19))] if d]
            ret = np.array([d["ret"] for d in rows]); expo = np.array([d["send"] + 1 for d in rows])   # S - B
            gas = sim.GAS / sim.STAKES[s]
            res = {"n": len(rows), "mean_no_reaction": float(ret.mean())}
            for r in (0.25, 0.5, 0.96):
                pl = np.array([r * p_le(x) for x in expo])
                ev = (1 - pl) * ret + pl * (-1 - gas)
                res[f"ev_r{r}"] = float(ev.mean())
            res["exposure_p50"] = float(np.median(expo)); res["P_loss_r0.96_mean"] = float(np.mean([0.96 * p_le(x) for x in expo]))
            out[f"{tp} K{K} stake{sim.STAKES[s]/1e18:g}"] = res
            print(f"{tp} K{K} stake {sim.STAKES[s]/1e18:g}: n {len(rows)} no-reaction {100*ret.mean():+6.2f}% | exposure S-B p50 {np.median(expo):.0f} "
                  f"| EV if react 25% {100*res['ev_r0.25']:+6.2f}%  50% {100*res['ev_r0.5']:+6.2f}%  96% {100*res['ev_r0.96']:+6.2f}% (P(-100%) {100*res['P_loss_r0.96_mean']:.1f}%)")
json.dump(out, open("chk/react_ev.json", "w"), indent=1)
