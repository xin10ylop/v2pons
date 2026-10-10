"""Expected return per launch if the engine arms from the launch RECEIPT (fires when the receipt arrives: feed blocks elapsed, from the
live probe yday/seat_rpc_lag_probe.json, 231 txs) vs from the calldata (fire in the launch block or the next). Population replay (633 pools)."""
import json, collections, statistics as st, sys
sys.path.insert(0, "adv")
import popreplay as PR
import advreplay as R
lag = [x["blocks"] for x in json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/yday/seat_rpc_lag_probe.json")) if x.get("blocks") is not None]
c = collections.Counter(lag); n = len(lag)
print("receipt lag (feed blocks) distribution:", sorted(c.items()))
from pickle import load
P = PR.P; FP = PR.FP
Qs = [PR.mkQ(p, "inwin") for p in P.values() if PR.isf(p)] + [PR.mkQ(p, "fwd") for p in FP.values() if PR.isf(p)]
res = {}
for X_ in (0.0012, 0.006):
    for K in range(0, 14):
        rs = [r["ret"] for Q in Qs for r in [R.trade(Q, K, int(X_ * 1e18))] if r["ret"] is not None]
        res[(X_, K)] = st.mean(rs)
    ev = sum(c[k] / n * res[(X_, k)] for k in c if (X_, k) in res)
    print(f"X {X_}: mean ret by fire offset K (land K+1):", " ".join(f"K{k}:{100*res[(X_, k)]:+.1f}%" for k in range(0, 14)))
    print(f"   EV if firing at the receipt (probe lags): {100*ev:+.2f}% per launch;  firing from calldata (K=0..2): {100*res[(X_, 1)]:+.2f}%")
