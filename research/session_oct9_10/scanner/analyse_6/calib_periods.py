"""v2.433 front by period: before our live trading (< Oct 10 09:07 UTC), live before the operator's 0.00495-ETH pre-bot buys, after.
Also the room left ahead of the bot's buy per period, and the rule at smaller stakes in the last period."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools()
v2 = sorted([pid for pid, p in P.items() if p["known"] == "vbot-v2.433"], key=lambda k: P[k]["launch_block"])
E = load_events(set(v2)); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
LIVE = 1791624420                  # Oct 10 09:07 UTC
big_ahead = lambda pl, b: [x for x in pl.buys() if not is_bot(x) and x["eth"] >= int(0.001e18) and (x["bn"], x["li"]) < (b["bn"], b["li"])]
first_def = None
per = collections.defaultdict(list); rooms = collections.defaultdict(list); stakes = collections.defaultdict(lambda: collections.defaultdict(list))
for pid in v2:
    pl = Pool(P[pid], E.get(pid), T, M); p = P[pid]
    b = next((x for x in pl.buys() if is_bot(x)), None)
    ba = big_ahead(pl, b) if b else []
    if ba and first_def is None: first_def = (p["launch_ts"], pid, [(x["rel"], x["eth"] / 1e18, x["to"]) for x in ba])
    if first_def is None or p["launch_ts"] < first_def[0]:
        k = "a_before_live" if p["launch_ts"] < LIVE else "b_live_before_defense"
    else:
        k = "c_defense_era"
    per[k].append(front(pl, is_bot, minout=vbot_minout))
    if b:
        s, L = pl.state_before(b); rooms[k].append(room(s, L, b["eth"], b["fee"], vbot_minout(b)))
    per[k + "|big_ahead" if ba else k + "|no_big_ahead"].append(per[k][-1])
    if k == "c_defense_era":
        for stake in (0.002, 0.003, 0.004, 0.005, 0.0058):
            X = int(stake * 1e18)
            B = pl.b0 + 1; sch = [x for x in pl.buys() if is_bot(x) and x["bn"] > B]
            S = min(sch[0]["bn"] + 1, pl.b0 + 20) if sch else pl.b0 + 20
            stakes[k][stake].append(pl.trade(B, S, stake=X, minout=vbot_minout))
out = {"first_defense_pool": first_def, "periods": {k: summarize(v) for k, v in sorted(per.items())},
       "room_left_eth_p10_50_90": {k: pct(v) for k, v in rooms.items()},
       "room_left_lt_0.0058": {k: sum(1 for a in v if a < 0.0058) for k, v in rooms.items()}, "n_room": {k: len(v) for k, v in rooms.items()},
       "defense_era_by_stake": {f"{k}|{s}": summarize(v) for k, d in stakes.items() for s, v in d.items()}}
json.dump(out, open(os.path.join(HERE, "calib_periods.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
