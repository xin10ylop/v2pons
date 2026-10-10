"""pool by pool: the pricer's front trade at the live stake and the live buy/sell offsets vs the relay's real return (front_audit/full_audit.json)"""
import sys, os, json, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
A = json.load(open("/home/user/v2pons/research/session_oct9_10/front_audit/full_audit.json"))
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pre = {pid[:10]: pid for pid in P}
pids = set(pre[a["pid"]] for a in A if a["pid"] in pre)
E = load_events(pids)
d = []; rows = []
for a in A:
    pid = pre.get(a["pid"])
    if not pid or a.get("ret") is None or a.get("fee") != 2500: continue
    pool = Pool(P[pid], E[pid], T, M); b0 = pool.b0
    r = pool.trade(b0 + a["buy_off"], b0 + a["sell_off"], stake=int(round(a["stake"] * 1e18)))
    if r.get("ret") is None: continue
    # the live ret is gross of gas? compare gross
    rows.append((a["pid"], a["stake"], round(a["ret"], 5), round(r["gross"], 5), round(r["ret"], 5)))
    d.append(r["gross"] - a["ret"])
print("n", len(d), "median diff (pricer gross - live)", st.median(d), "mean", st.mean(d), "p05/p95", sorted(d)[len(d) // 20], sorted(d)[-len(d) // 20])
print("mean live", st.mean(x[2] for x in rows), "mean pricer gross", st.mean(x[3] for x in rows), "net", st.mean(x[4] for x in rows))
json.dump({"n": len(d), "median_diff_gross_minus_live": st.median(d), "mean_diff": st.mean(d), "mean_live": st.mean(x[2] for x in rows),
           "mean_pricer_gross": st.mean(x[3] for x in rows), "mean_pricer_net": st.mean(x[4] for x in rows), "rows": rows}, open("calib_live.json", "w"), indent=0)
