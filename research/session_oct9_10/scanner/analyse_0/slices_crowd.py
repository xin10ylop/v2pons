"""Stability of the chosen crowd-riding variants by 6-hour slice, and their loss tail. fee100-2276: entry one block after the first crowd
buy (0xd6d35b56 e6cb474f), exit at entry + 50 / + 100 blocks. pm-init-500: entry at the add block + 1, exit at + 200; entry one block after
the first crowd buy (7169b574), exit at entry + 100."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_minout, time_bucket
P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
VAR = {"fee100-2276": ("0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true", 2, [("crowd1+1", 50), ("crowd1+1", 100)]),
       "pm-init-500": ("0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", 3, [("live+1", 200), ("crowd1+1", 100), ("crowd1+1", 50)])}
out = {}
for name, (key, idx, vars_) in VAR.items():
    pids = FF[key]["pids"]; E = load_events(set(pids)); mo = sched_minout(name)
    rows = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, f"pools_{idx}.jsonl"))}
    for entry, H in vars_:
        sl = collections.defaultdict(list); allr = []
        for pid in pids:
            pl = Pool(P[pid], E[pid], T, M); r = rows[pid]
            if entry == "live+1": B = pl.live_block + 1
            else:
                if not r["sched"]: continue
                B = pl.live_block + r["sched"]["off"] + 1
            t = pl.trade(B, B + H if entry != "live+1" else pl.live_block + H, minout_check=mo)
            sl[time_bucket(pl.p["launch_ts"])].append(t); allr.append(t)
        k = f"{name}|{entry}|H{H}"
        out[k] = {"all": summarize(allr), "by_6h": {b: {kk: v for kk, v in summarize(rs).items() if kk in ("n", "mean", "median", "win", "pulled_first")} for b, rs in sorted(sl.items())}}
        print(k, json.dumps(out[k]["all"]))
        for b, v in out[k]["by_6h"].items(): print("   ", b, v)
json.dump(out, open(os.path.join(HERE, "slices_crowd.json"), "w"), indent=1)
