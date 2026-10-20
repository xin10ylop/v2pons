# every 7fde822e launch in the census: per deployer, how many pools get a real buy (>= 0.0002 ETH), when, from whom, pulls
import sys, collections, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
pids = [p["pid"] for p in P.values() if p["selector"] == "7fde822e"]
E = load_events(set(pids))
by = collections.defaultdict(list)
for pid in pids: by[P[pid]["launch_from"]].append(pid)
out = {}
for d, pl in sorted(by.items(), key=lambda kv: -len(kv[1])):
    real = []; pulls = 0; ethin = 0; froms = collections.Counter(); lens = collections.Counter(); spans = []
    for pid in pl:
        p = P[pid]; e = E.get(pid) or {"swaps": [], "pulls": []}
        lens[(p["calldata_len"], p["fee"], p["tick_spacing"], p["launch_value_eth"])] += 1
        rb = [s for s in e["swaps"] if s["a0"] < 0 and -s["a0"] >= int(0.0002e18) and s["tx"] != p["launch_tx"]]
        if rb:
            t = T.get(rb[0]["tx"])
            real.append((pid[:10], rb[0]["bn"] - p["launch_block"], round(-rb[0]["a0"] / 1e18, 6), t and t["from"][:10], t and (t["to"] or "")[:10], len(rb)))
        pulls += bool(e["pulls"]); ethin += sum(-s["a0"] for s in e["swaps"] if s["a0"] < 0)
    bl = sorted(P[x]["launch_block"] for x in pl)
    out[d] = {"pools": len(pl), "with_real_buy": len(real), "pulled_3000": pulls, "eth_in_all_buys": ethin / 1e18, "layouts": [list(k) + [v] for k, v in lens.most_common(6)],
              "first_block": bl[0], "last_block": bl[-1], "median_gap_blocks": sorted(b - a for a, b in zip(bl, bl[1:]))[len(bl) // 2] if len(bl) > 2 else None,
              "real_buys": real[:12]}
    print(d, json.dumps(out[d]))
json.dump(out, open("sel7fde.json", "w"), indent=1)
