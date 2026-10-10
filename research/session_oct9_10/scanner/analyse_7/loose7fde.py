"""robustness: the whole 7fde822e launcher (every launch contract, every deployer, every calldata length) priced the same way"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
pids = [pid for pid, p in P.items() if p["selector"] == "7fde822e"]
E = load_events(set(pids))
fr_ = []; fo_ = []; real = []; pulls = 0; tick0 = collections.Counter(); liq = collections.Counter(); deps = collections.Counter(); tos = set()
for pid in pids:
    pool = Pool(P[pid], E.get(pid), T, M); b0 = pool.b0; bs = pool.buys()
    deps[P[pid]["launch_from"]] += 1; tos.add(P[pid]["launch_to"]); tick0[(P[pid]["tick0"], P[pid]["fee"], P[pid]["tick_spacing"])] += 1; liq[P[pid]["liq_launch"]] += 1
    sb = next((x for x in bs if x["eth"] >= MIN_REAL), None)
    if sb: real.append((pid[:10], sb["bn"] - b0, round(sb["eth"] / 1e18, 6), sb["to"], sb["from"]))
    pulls += pool.pull_bn is not None
    S = sb["bn"] + 1 if (sb and b0 + 1 < sb["bn"] <= b0 + 19) else b0 + 20
    if not (sb and sb["bn"] <= b0 + 1): fr_.append(pool.trade(b0 + 1, S))
    if sb:
        Bf = sb["bn"] + 1; nb = next((x for x in bs if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
        fo_.append(pool.trade(Bf, min(nb["bn"] + 1, Bf + 4) if nb else Bf + 4))
out = {"pools": len(pids), "launch_contracts": len(tos), "deployers": deps.most_common(), "tick0_fee_ts": tick0.most_common(3), "liq_launch": liq.most_common(3),
       "pulled_3000": pulls, "real_buys": real, "front": summarize(fr_), "follow": summarize(fo_)}
json.dump(out, open(os.path.join(HERE, "loose7fde.json"), "w"), indent=1)
print(json.dumps(out, indent=0)[:3000])
