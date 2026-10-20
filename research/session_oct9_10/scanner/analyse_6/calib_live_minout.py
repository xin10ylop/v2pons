"""Check the minOut model on the chain: in v2.433 pools where our relay bought ahead of the bot, total ETH ahead of the bot's buy on the
real chain (relay included) vs whether the bot's buy happened, and the model's room for those pools."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools()
v2 = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
E = load_events(set(v2)); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
DEF = 1791643901
rows = []
for pid in v2:
    pl = Pool(P[pid], E.get(pid), T, M)
    rb = [x for x in pl.seq if x["relay"] and x["buy"]]
    if not rb: continue
    b = next((x for x in pl.seq if x["buy"] and is_bot(x)), None)
    ahead = None; real_room = None
    if b:
        ah = [x for x in pl.seq if x["buy"] and not x["in_launch"] and (x["bn"], x["li"]) < (b["bn"], b["li"])]
        ahead = sum(x["eth"] for x in ah) / 1e18
        real_room = room(pl.s_eff, pl.L0, b["eth"], b["fee"], vbot_minout(b))
        # the bot's output on the chain vs its minOut: the headroom ratio
        hr = b["a1"] / vbot_minout(b)
    else:
        ah = [x for x in pl.seq if x["buy"] and not x["in_launch"] and x["rel"] <= 20]
        ahead = sum(x["eth"] for x in ah) / 1e18; hr = None
    rows.append({"pid": pid, "defense": P[pid]["launch_ts"] >= DEF, "bot": bool(b), "bot_rel": b and b["rel"], "eth_ahead_incl_relay": ahead, "room_model": real_room,
                 "bot_out_over_minout": hr, "relay_buy_rel": rb[0]["rel"], "relay_eth": rb[0]["eth"] / 1e18, "pull": pl.pull_bn and pl.pull_bn - pl.b0})
c = collections.Counter((r["defense"], r["bot"]) for r in rows)
print("relay pools by (defense era, bot buy seen):", dict(c))
d = [r for r in rows if r["defense"]]
print("defense era, bot seen: eth ahead p10/50/90", pct([r["eth_ahead_incl_relay"] for r in d if r["bot"]]), "out/minOut", pct([r["bot_out_over_minout"] for r in d if r["bot"]]))
print("defense era, no bot: eth ahead (first 20 blocks) p10/50/90", pct([r["eth_ahead_incl_relay"] for r in d if not r["bot"]]), "relay eth", pct([r["relay_eth"] for r in d]))
print("pre-defense relay pools, bot seen: eth ahead", pct([r["eth_ahead_incl_relay"] for r in rows if not r["defense"] and r["bot"]]), "out/minOut", pct([r["bot_out_over_minout"] for r in rows if not r["defense"] and r["bot"]]))
mx = max((r["eth_ahead_incl_relay"] for r in rows if r["bot"]), default=None); print("max eth ahead with the bot's buy still landing:", mx)
json.dump(rows, open(os.path.join(HERE, "calib_live_minout.json"), "w"), indent=1)
