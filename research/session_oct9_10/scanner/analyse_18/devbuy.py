"""openlaunch (0x815542e8) wider group: front at launch+1, sold one block after the launch wallet's own (dev) buy, else at launch + H,
for H = 20, 100, 3000: does waiting for the dev buy pay? and the same on the assigned 833/30000 family"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common18 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta(); F = load_families()
K = json.load(open(os.path.join(HERE, "keys.json")))
grp = {"openlaunch all": [p["pid"] for p in P.values() if p["launch_to"] == "0x815542e8b392389a1389e22e588e4b62a67ade72"], "assigned " + K[1][:20]: F[K[1]]["pids"]}
E = load_events(set(x for v in grp.values() for x in v))
out = {}
for g, pids in grp.items():
    for H in (20, 100, 3000):
        rs = []
        for x in pids:
            pl = Pool(P[x], E.get(x), T, M); lb = pl.b0
            dev = next((y for y in pl.buys() if y["from"] == P[x]["launch_from"] and y["eth"] >= MIN_REAL and y["bn"] > lb + 1), None)
            S = dev["bn"] + 1 if dev and dev["bn"] + 1 <= lb + H else lb + H
            r = pl.trade(lb + 1, S); r["dev"] = (dev["bn"] - lb, dev["eth"] / 1e18) if dev else None; rs.append(r)
        s = summarize(rs); out[f"{g} H{H}"] = s
        print(g, "H", H, fmt_rule(s))
        if H == 100: print("    dev-buy pools:", [(r["dev"], round(r["ret"], 4)) for r in rs if r["dev"]])
json.dump(out, open(os.path.join(HERE, "devbuy.json"), "w"), indent=1)
