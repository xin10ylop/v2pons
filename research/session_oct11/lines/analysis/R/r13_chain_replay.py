"""Chain replay (the $/day = $/trade x the line's launches/day over the last 90 min x the share of untouched launches with a bot buy) of the ride (task 2) on the last 6 h, untouched pools: buy q at the head of T+2 (T+1 = upper bound), exits a/b/c (ride.py);
the bot's later buys are dropped when our buy pushes their output under their calldata minOut. By regime; also priced with the census reaction
(pull at our buy + 7). $/day at the current launch rate (the last 60 / 90 minutes)."""
import pickle, collections, json
from common import *
from ride import *
import v4math
D = pickle.load(open("chpools.pkl", "rb")); P = D["pools"]
REG = ["2.433 fee2500", "2.433 fee5000<16:28", "2.433 fee5000>=16:28", "3.0 new"]
head_ts = D["head_ts"]
rate = {}
for line in ("2.433", "3.0"):
    for mins in (60, 90, 180):
        n = sum(1 for p in P if p["line"] == line and p["ts"] >= head_ts - mins * 60)
        rate[(line, mins)] = n * 1440 / mins
print("launch rate per day from the last 60/90/180 min:", {k: round(v) for k, v in rate.items()})
def mkskip(fee_pool):
    def skip(s, sp, L):
        if s.get("who") == "bot" and s.get("minout"):
            return v4math.buy_out_int(sp, L, s["q"], fee_pool) < s["minout"]
        return False
    return skip
U = [p for p in P if not p["ours"] and p["T"] is not None]
out = {}; lines = []
for react in (None, 7):
    for reg in REG + ["2.433 fee5000 all", "ALL 6h 2.433", "ALL 6h 3.0"]:
        if reg == "2.433 fee5000 all": G = [p for p in U if p["line"] == "2.433" and p["fee"] == 5000]
        elif reg.startswith("ALL"): G = [p for p in U if p["line"] == reg.split()[-1]]
        else: G = [p for p in U if p["regime"] == reg]
        if not G: continue
        line = G[0]["line"]; nl = sum(1 for p in P if not p["ours"] and ((p["regime"] == reg) or (reg.startswith("ALL") and p["line"] == line) or (reg == "2.433 fee5000 all" and p["line"] == "2.433" and p["fee"] == 5000)))   # untouched launches: share with a bot buy
        for q in QS:
            for lag in (2, 1):
                if lag == 1 and q != 0.0058: continue
                R = collections.defaultdict(list); inc = collections.Counter()
                for p in G:
                    fo = 5000 if line == "2.433" else 10000
                    pp = dict(p)
                    if react is not None:
                        fake = p["T"] + lag + react; pp["pull"] = fake if p["pull"] is None else min(p["pull"], fake)
                    res = run_pool(pp, q, lag, fo, fee_pool=p["fee"], skip=mkskip(p["fee"]))
                    for name, r in res.items():
                        if r["S"] > p["span"] and r["why"] != "pulled": inc[name] += 1; continue
                        R[name].append(r)
                for name in sorted(R):
                    s = summ(R[name], q, rate[(line, 90)], len(G) / max(1, nl))
                    s["incomplete"] = inc[name]; s["dropped_bot_buys"] = sum(r.get("dropped", 0) for r in R[name])
                    k = f"{'react+7 ' if react else ''}{reg}|q{q}|T+{lag}|{name}"; out[k] = s
                    lines.append(f"{'react+7 ' if react else '':8s}{reg:21s} q{q:<6} T+{lag} {name:12s} n {s['n']:3d} mean {s.get('mean%',0):+7.2f}% med {s.get('med%',0):+7.2f}% win {s.get('win',0):.3f} worst {s.get('worst%',0):+7.1f}% "
                                 f"pulled {s.get('pulled',0):3d} ({s.get('pulled%',0):5.1f}%) $/tr {s.get('usd_tr',0):+.4f} $/day {s.get('usd_day',0):+8.2f} incompl {inc[name]} botbuys-dropped {s['dropped_bot_buys']}")
json.dump(out, open("r13_chain_replay.json", "w"), indent=0)
open("r13_chain_replay.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(l for l in lines if " q0.0058 T+2 " in l))
