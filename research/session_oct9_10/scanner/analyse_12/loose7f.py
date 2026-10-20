"""the whole 7fde822e operator (family 1 is one of its ~27 launch contracts): does any of its 490 pools get a real buy or a pull?"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from px import *  # noqa
P = load_pools()
ps = [p for p in P.values() if p["selector"] == "7fde822e"]
E = load_events(set(p["pid"] for p in ps))
mx = []; nreal = 0; senders = collections.Counter(); deps = collections.Counter(p["launch_from"] for p in ps)
for p in ps:
    e = E.get(p["pid"]) or {"swaps": [], "pulls": []}
    b = [s for s in e["swaps"] if s["a0"] < 0]
    m = max([-s["a0"] for s in b], default=0); mx.append(m / 1e18)
    if m >= MIN_REAL: nreal += 1
    for s in b: senders[s["sender"]] += 1
blocks = sorted(p["launch_block"] for p in ps)
res = {"pools": len(ps), "per_day": round(len(ps) / WINDOW_DAYS, 1), "deployers": deps.most_common(6), "launch_contracts": len(set(p["launch_to"] for p in ps)),
       "pools_with_a_buy_ge_0.0002": nreal, "max_buy_eth_p50_90_99_max": q(mx, (.5, .9, .99, 1.0), nd=8),
       "pools_pulled": sum(1 for p in ps if p["first_pull_rel"] is not None), "swap_senders": senders.most_common(5),
       "first_last_block": [blocks[0], blocks[-1]], "values": collections.Counter(p["launch_value_eth"] for p in ps).most_common(3)}
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(HERE, "loose7f.json"), "w"), indent=1)
