"""Finer holds for the crowd families' riding variants (sensitivity, not a pick): pm-init-500 live+1 exits at +150..+220 (a pull cluster
sits at +223..+232 after the add block); fee100-2276 crowd1+1 holds 20..100."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_minout
P = load_pools(); T = load_txs(); M = load_blocks_meta(); FF = load_families()
out = {}
for name, key, idx, entry, Hs in (("pm-init-500", "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", 3, "live+1", range(150, 230, 10)),
                                  ("pm-init-500", "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", 3, "crowd1+1", range(20, 160, 20)),
                                  ("fee100-2276", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true", 2, "crowd1+1", range(20, 110, 10))):
    pids = FF[key]["pids"]; E = load_events(set(pids)); mo = sched_minout(name)
    rows = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, f"pools_{idx}.jsonl"))}
    pls = [Pool(P[p], E[p], T, M) for p in pids]
    for H in Hs:
        rs = []
        for pl in pls:
            r = rows[pl.pid]
            if entry == "live+1": rs.append(pl.trade(pl.live_block + 1, pl.live_block + H, minout_check=mo))
            elif r["sched"]:
                B = pl.live_block + r["sched"]["off"] + 1; rs.append(pl.trade(B, B + H, minout_check=mo))
        s = summarize(rs); out[f"{name}|{entry}|H{H}"] = s
        print(f"{name}|{entry}|H{H}", {k: s[k] for k in ("n", "mean", "median", "win", "pulled_first", "usd_trade", "usd_day")})
json.dump(out, open(os.path.join(HERE, "fine_grid.json"), "w"), indent=1)
