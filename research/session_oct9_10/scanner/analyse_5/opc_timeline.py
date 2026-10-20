"""every swap of the opC pools with its transaction (census + opc_txs.json): who is the crowd (nonce-0 wallet, UR 1284 bytes), who else buys
and sells, and when the pull comes relative to the 10th crowd buy and to each outsider. Writes opc_timeline.json"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer import *
P = load_pools(); T = load_txs(); F = load_families()
X = json.load(open(os.path.join(HERE, "opc_txs.json")))
keys = ["0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"]
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))
tx = lambda h: T.get(h) or X.get(h)
out = []; who = collections.defaultdict(lambda: {"buys": 0, "sells": 0, "eth_buy": 0, "eth_sell": 0, "pools": set(), "lens": collections.Counter(), "nonce0": 0})
for pid in pids:
    p = P[pid]; e = E[pid]; b0 = p["launch_block"]; rows = []
    for s in e["swaps"]:
        t = tx(s["tx"]); buy = s["a0"] < 0
        crowd = bool(t and buy and t["to"] == UR and t["calldata_len"] == 1284 and t["nonce"] == 0)
        rows.append({"off": s["bn"] - b0, "side": "B" if buy else "S", "eth": abs(s["a0"]) / 1e18, "from": t["from"], "to": t["to"], "len": t["calldata_len"], "nonce": t["nonce"], "crowd": crowd})
        w = who["crowd" if crowd else t["from"]]; w["pools"].add(pid); w["lens"][t["calldata_len"]] += 1
        if buy: w["buys"] += 1; w["eth_buy"] += abs(s["a0"]) / 1e18
        else: w["sells"] += 1; w["eth_sell"] += abs(s["a0"]) / 1e18
    crowd = [r for r in rows if r["crowd"]]
    pull = e["pulls"][0]["bn"] - b0 if e["pulls"] else None
    pt = tx(e["pulls"][0]["tx"]) if e["pulls"] else None
    outs = [r for r in rows if not r["crowd"] and r["side"] == "B" and r["eth"] >= 0.0002]
    out.append({"pid": pid, "fee": p["fee"], "b0": b0, "value": p["launch_value_eth"], "n_crowd": len(crowd), "crowd_eth": round(sum(r["eth"] for r in crowd), 6),
                "crowd_offs": [r["off"] for r in crowd], "crowd_gaps": [b["off"] - a["off"] for a, b in zip(crowd, crowd[1:])],
                "pull": pull, "pull_from_launcher": (pt["from"] == p["launch_from"]) if pt else None, "pull_after_last_crowd": (pull - crowd[-1]["off"]) if (pull and crowd) else None,
                "outsider_buys": [(r["off"], round(r["eth"], 6), r["from"][:10]) for r in outs],
                "sells": [(r["off"], round(r["eth"], 6), r["from"][:10]) for r in rows if r["side"] == "S"]})
for o in out:
    print(o["pid"][:10], o["fee"], o["value"], "crowd", o["n_crowd"], o["crowd_eth"], o["crowd_offs"], "pull", o["pull"], "after last", o["pull_after_last_crowd"])
    print("     outsiders>=0.0002", o["outsider_buys"]); print("     sells", o["sells"])
W = {k: {"buys": v["buys"], "sells": v["sells"], "eth_buy": round(v["eth_buy"], 6), "eth_sell": round(v["eth_sell"], 6), "pools": len(v["pools"]), "lens": dict(v["lens"])} for k, v in who.items()}
print(json.dumps(dict(sorted(W.items(), key=lambda kv: -kv[1]["pools"])), indent=0)[:3000])
json.dump({"pools": out, "who": W}, open(os.path.join(HERE, "opc_timeline.json"), "w"), indent=1)
