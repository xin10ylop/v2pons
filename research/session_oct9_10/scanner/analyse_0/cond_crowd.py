"""The crowd-riding variants restricted to the pools that already had an outsider in front of the crowd (our own buy makes every pool such
a pool): fee100-2276 with a non-crowd buy >= 0.0002 ETH before the first crowd buy; pm-init-500 with the 9.5e-5 ETH sniper."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_minout
P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
out = {}
SN = "0xe9d83e95b2248d8b33d63583762bd7f7465ddb28"
for name, key, idx, cond, variants in (
        ("fee100-2276", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true", 2,
         lambda r: any(o["cls"] == "other" and o["eth"] >= 0.0002 for o in r["before_sched"]), [("crowd1+1", 50), ("crowd1+1", 100)]),
        ("pm-init-500", "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", 3,
         lambda r: any(o["from"] == SN for o in r["before_sched"]), [("live+1", 180), ("live+1", 200), ("crowd1+1", 100)])):
    pids = FF[key]["pids"]; E = load_events(set(pids)); mo = sched_minout(name)
    rows = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, f"pools_{idx}.jsonl"))}
    for entry, H in variants:
        res = {"with": [], "without": []}
        for pid in pids:
            r = rows[pid]
            if not r["sched"]: continue
            pl = Pool(P[pid], E[pid], T, M)
            if entry == "live+1": t = pl.trade(pl.live_block + 1, pl.live_block + H, minout_check=mo)
            else:
                B = pl.live_block + r["sched"]["off"] + 1; t = pl.trade(B, B + H, minout_check=mo)
            res["with" if cond(r) else "without"].append(t)
        k = f"{name}|{entry}|H{H}"
        out[k] = {g: {kk: v for kk, v in summarize(rs).items() if kk in ("n", "mean", "median", "win", "pulled_first", "usd_trade")} for g, rs in res.items()}
        print(k, json.dumps(out[k]))
json.dump(out, open(os.path.join(HERE, "cond_crowd.json"), "w"), indent=1)
