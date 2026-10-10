"""Skeptic f2276/100 step 9: the six outsider buys followed by a pull within 100 blocks, swap by swap (is the pull a reaction to the
outsider, or the pool dying: the crowd stopped and the creator pulled as it does in every dead pool?), and the same 'death' measure
(blocks from the last buy >= 0.01 ETH to the pull) in all pulled pools."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
P = load_pools(); F = load_families(); T = load_txs(); pids = F[K]["pids"]; E = load_events(set(pids))
quick = ["0xc11b63f9", "0x54d15595", "0xee1a2e29", "0xae0afacf", "0xf9559176", "0xeef312bd"]
for pid in pids:
    if pid[:10] not in quick: continue
    e = E[pid]; b0 = P[pid]["launch_block"]; pull = e["pulls"][0]["bn"]
    print("== pool", pid[:10], "pull at +%d" % (pull - b0))
    for s in e["swaps"]:
        if s["bn"] > pull: break
        t = T.get(s["tx"]); who = ("APP" if t and t["to"] == CROWD else (t["from"][:10] if t else "?")) if t else "?(no tx)"
        print("   +%4d %s %.5f %s" % (s["bn"] - b0, "B" if s["a0"] < 0 else "S", abs(s["a0"]) / 1e18, who))
dead = []
for pid in pids:
    e = E[pid]
    if not e["pulls"]: continue
    pull = e["pulls"][0]["bn"]; big = [s for s in e["swaps"] if s["a0"] < -1e16 and s["bn"] <= pull]
    if big: dead.append(pull - big[-1]["bn"])
print("all pulled pools with a buy >= 0.01: blocks from the last such buy to the pull q", q(dead), "n", len(dead))
