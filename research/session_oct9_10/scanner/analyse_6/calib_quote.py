"""What state does the volume bot quote its minOut at? For each v2.433 bot buy: minOut / quote(launch state) and minOut / quote(the real
state just before its buy, every earlier swap included), by era (before our live trading, live before its 0.00495 pre-buys, after)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools()
v2 = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
E = load_events(set(v2)); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
LIVE, DEF = 1791624420, 1791643901
R = collections.defaultdict(lambda: collections.defaultdict(list))
for pid in v2:
    pl = Pool(P[pid], E.get(pid), T, M); ts = P[pid]["launch_ts"]
    era = "a_before_live" if ts < LIVE else ("b_live" if ts < DEF else "c_defense")
    b = next((x for x in pl.seq if x["buy"] and is_bot(x)), None)
    if not b: continue
    mo = vbot_minout(b)
    q_launch = v4math.buy_out_int(pl.s_eff, pl.L0, b["eth"], b["fee"])
    q_pre = v4math.buy_out_int(b["prev_sp"], pl.L0, b["eth"], b["fee"])          # the real chain state before its buy (everything included)
    ahead = sum(x["eth"] for x in pl.seq if x["buy"] and not x["in_launch"] and (x["bn"], x["li"]) < (b["bn"], b["li"])) / 1e18
    k = "with_ahead>=0.005" if ahead >= 0.005 else "ahead<0.005"
    for kk in (era, era + "|" + k):
        R[kk]["mo_over_qlaunch"].append(mo / q_launch); R[kk]["mo_over_qpre"].append(mo / q_pre); R[kk]["ahead"].append(ahead)
out = {k: {a: [round(x, 5) for x in pct(v)] for a, v in d.items()} | {"n": len(d["ahead"])} for k, d in sorted(R.items())}
json.dump(out, open(os.path.join(HERE, "calib_quote.json"), "w"), indent=1)
for k, v in out.items(): print(k, v)
