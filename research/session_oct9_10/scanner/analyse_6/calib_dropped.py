"""Why the bot's buy is dropped in some v2.433 pools: who buys ahead of it."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools()
v2 = [pid for pid, p in P.items() if p["known"] == "vbot-v2.433"]
E = load_events(set(v2)); T = load_txs(); M = load_blocks_meta()
is_bot = lambda x: x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d"
ahead_who = collections.Counter(); ahead_eth = collections.defaultdict(list); nd = 0; ex = []
hourly = collections.defaultdict(lambda: [0, 0])
for pid in v2:
    pl = Pool(P[pid], E.get(pid), T, M)
    r = front(pl, is_bot, minout=vbot_minout)
    b = next((x for x in pl.buys() if is_bot(x)), None)
    h = (P[pid]["launch_ts"] - 1791483648) // 3600
    hourly[h][0] += 1
    if not r.get("dropped"): continue
    hourly[h][1] += 1
    nd += 1
    ah = [x for x in pl.seq if not x["relay"] and x["buy"] and not x["in_launch"] and (x["bn"], x["li"]) < (b["bn"], b["li"])]
    for x in ah:
        ahead_who[(x["from"], x["to"], x["sel"])] += 1; ahead_eth[(x["from"], x["to"], x["sel"])].append(x["eth"] / 1e18)
    if len(ex) < 8: ex.append({"pid": pid, "ret": r["ret"], "bot_rel": b["rel"], "bot_eth": b["eth"] / 1e18, "ahead": [(x["rel"], x["eth"] / 1e18, x["from"], x["to"], x["sel"]) for x in ah]})
print("dropped", nd)
for k, c in ahead_who.most_common(15): print(c, k, pct(ahead_eth[k]))
for e in ex: print(e)
print("hourly (h from window start: pools, dropped):", {k: v for k, v in sorted(hourly.items()) if v[0]})
