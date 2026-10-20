"""Calibrate the analyse_6 pricer on the two known families (controls): vbot-v2.433 (front) and operator A (follow)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *

P = load_pools()
v2 = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
opa = [pid for pid, p in P.items() if p["known"] == "operator-A"]
E = load_events(set(v2) | set(opa)); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
out = {}

# ---- v2.433 front
rs, rs_live, rs_before, caps_total, caps_left, nobot, relay_pools, beyond8 = [], [], [], [], [], 0, 0, 0
for pid in v2:
    pl = Pool(P[pid], E.get(pid), T, M)
    if pl.L0 <= 0: continue
    r = front(pl, is_bot, minout=vbot_minout)
    rs.append(r)
    has_relay = any(x["relay"] for x in pl.seq)
    if has_relay: relay_pools += 1; rs_live.append(r)
    else: rs_before.append(r)
    b = next((x for x in pl.buys() if is_bot(x)), None)
    if b is None:
        nobot += 1
        if any(not x["known_tx"] for x in pl.seq if x["buy"]): beyond8 += 1
        continue
    mo = vbot_minout(b)
    # room from the launch state (total ETH that can sit ahead) and what is left after the real non-relay buys ahead of it
    L0 = pl.L0
    caps_total.append(room(pl.s_eff, L0, b["eth"], b["fee"], mo))
    s_pre, L_pre = pl.state_before(b)
    caps_left.append(room(s_pre, L_pre, b["eth"], b["fee"], mo))
out["v2433_front"] = {"pools": len(rs), "all": summarize(rs), "pools_with_our_relay": summarize(rs_live), "pools_before_our_trading": summarize(rs_before),
                      "no_bot_buy_identified": nobot, "no_bot_buy_but_unfetched_swaps": beyond8,
                      "room_total_eth_p10_50_90": pct(caps_total), "room_left_eth_p10_50_90": pct(caps_left), "n_room": len(caps_total),
                      "sched_rel_p10_50_90": pct([r["sched_rel"] for r in rs]),
                      "dropped_bot_buys": sum(1 for r in rs if r.get("dropped"))}
# B_off sensitivity
out["v2433_front_by_Boff"] = {}
for k in (1, 2, 3):
    out["v2433_front_by_Boff"][k] = summarize([front(Pool(P[pid], E.get(pid), T, M), is_bot, minout=vbot_minout, B_off=k) for pid in v2])

# ---- operator A follow (and front for reference)
fr, fo = [], []
for pid in opa:
    pl = Pool(P[pid], E.get(pid), T, M)
    if pl.L0 <= 0: continue
    fo.append(follow(pl))
    fr.append(front(pl, lambda x: x["eth"] >= MIN_REAL))
out["opA_follow"] = summarize(fo)
out["opA_follow_trig_rel_p10_50_90"] = pct([r["trig_rel"] for r in fo if r])
out["opA_front"] = summarize(fr)
for h in (2, 3, 6, 10):
    out[f"opA_follow_hold{h}"] = summarize([follow(Pool(P[pid], E.get(pid), T, M), hold=h) for pid in opa])
json.dump(out, open(os.path.join(HERE, "calib.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
