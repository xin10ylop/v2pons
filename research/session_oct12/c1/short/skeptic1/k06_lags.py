"""Skeptic 1: the shortest reaction lags, event by event (offline, k01_pools.json). Every outside >= 0.001 ETH buy after the engine's T
(held >= 30 blocks or into the pull), plus our 5 fills: lag from the buy to the router's last buy before the pull and to the pull, the
router's buys in between, the pool's T and launch offsets. Lists every event pulled within 120 blocks of the buy."""
import json, time
from k02_sim import *
D = load(); P = D["pools"]
def rb(p, a, b): return [s for s in p["sw"] if s["c"] == "router" and s["buy"] and a < s["bn"] <= b and (p["pullpos"] is None or (s["bn"], s["li"]) < tuple(p["pullpos"]))]
ev = []
for p in P:
    T = p["Teng"] if p["Teng"] is not None else p["T"]
    if T is None or p["pullpos"] is None: continue
    done = set()
    for s in p["sw"]:
        if not s["buy"] or s["c"] not in ("out", "ours") or s["eth_wei"] < 10 ** 15 or s["from"] in done: continue
        if (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        done.add(s["from"])
        sl = next((x for x in p["sw"] if not x["buy"] and x["from"] == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"])), None)
        held_to_pull = sl is None or (sl["bn"], sl["li"]) > tuple(p["pullpos"])
        if not held_to_pull and sl["bn"] - s["bn"] < 30: continue
        lag = p["pullpos"][0] - s["bn"]
        if lag > 120: continue
        b_before = rb(p, p["lb"], s["bn"]); b_after = rb(p, s["bn"], p["pullpos"][0])
        ev.append((lag, p["pid"][:10], s["c"], s["from"][:10], round(s["eth_wei"] / 1e18, 5), s["off"] - T, T, p["pull"], held_to_pull,
                   len(b_before), [x["bn"] - s["bn"] for x in b_after], time.strftime('%m-%d %H:%M', time.gmtime(p["ts"]))))
print("lag  pool       class wallet     ETH      h-T   T    pull(launch+)  held-to-pull  router buys before h | router buys after h (blocks after h)")
for e in sorted(ev):
    print(f"{e[0]:4d} {e[1]} {e[2]:5s} {e[3]} {e[4]:.5f} {e[5]:+5d} {e[6]:4d} {e[7]:5d}  {str(e[8]):5s}  {e[9]:3d} | {e[10][:10]}  {e[11]}")
