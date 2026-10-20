"""Census: 6-hour table per line: launches, ours, T p50, share pulled by T+3 / T+30 / T+400, share with a 2nd bot buy before the pull (untouched)."""
import pickle, collections, time
from common import *
P = pickle.load(open("cpools.pkl", "rb"))
for line in ("2.433", "3.0"):
    print(f"=== {line}")
    G = collections.defaultdict(list)
    for p in P:
        if p["line"] == line: G[int(p["ts"] // 21600)].append(p)
    for k in sorted(G):
        g = G[k]; u = [p for p in g if not p["ours"] and p["T"] is not None]; o = [p for p in g if p["ours"] and p["T"] is not None]
        def rate(gg, d): return f"{sum(1 for p in gg if p['pull'] is not None and p['pull'] <= p['T'] + d)}/{len(gg)}"
        def b2(gg):
            n = 0
            for p in gg:
                bots = [s for s in p["sw"] if s["who"] == "bot" and s["off"] >= p["T"]]
                if len(bots) > 1 and (p["pull"] is None or bots[1]["off"] < p["pull"]): n += 1
            return f"{n}/{len(gg)}"
        print(f"{time.strftime('%m-%d %H', time.gmtime(k*21600))}h n {len(g):4d} ours {len(o):4d} | untouched T50 {pct([p['T'] for p in u],.5)} pulled<=T+3 {rate(u,3):>8s} <=T+30 {rate(u,30):>8s} <=T+400 {rate(u,400):>8s} 2nd-bot-before-pull {b2(u):>8s}"
              f" | ours pulled<=T+3 {rate(o,3):>8s} 2nd-bot {b2(o)}")
