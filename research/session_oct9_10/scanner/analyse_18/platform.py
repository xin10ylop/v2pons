"""the 7fde822e (imortal.buzz) pools with any swap other than the dust bot's: who, when, how much (context for the trap/outsider notes)"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common18 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = [p["pid"] for p in P.values() if p["selector"] in ("7fde822e",) or p["launch_to"] == "0x815542e8b392389a1389e22e588e4b62a67ade72"]
E = load_events(set(pids))
for x in pids:
    pl = Pool(P[x], E.get(x), T, M)
    oth = [y for y in pl.seq if y["from"] != DUST]
    if not oth: continue
    print(P[x]["selector"], x[:12], "launch_from", P[x]["launch_from"][:10], "fee", P[x]["fee"], "pull", pl.pull_bn)
    for y in pl.seq:
        print("    +%-5d %s %.7f ETH to %s from %s sel %s" % (y["bn"] - pl.b0, "BUY " if y["buy"] else "SELL", y["eth"] / 1e18, (y["to"] or "?")[:12], (y["from"] or "?")[:12], y["sel"]))
