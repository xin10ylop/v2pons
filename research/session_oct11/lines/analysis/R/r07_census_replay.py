"""Census replay of the ride (task 2): buy q at the head of T+2 (and T+1), exits a/b/c (ride.py); untouched pools; by line, regime, day.
2.433 is replayed at the pool's fee (2500) and with our legs at 5000 (today's fee); 3.0 at 10000."""
import pickle, collections, json
from common import *
from ride import *
P = pickle.load(open("cpools.pkl", "rb"))
U = [p for p in P if not p["ours"] and p["T"] is not None]
def grp(p):
    if p["line"] == "3.0": return "d%d" % p["day"] + ("" if p["day"] < 6 else (" new" if p["ts"] >= NEW30 else " old"))
    return "d%d" % p["day"]
RES = collections.defaultdict(list)       # (line, fee_mode, q, lag, rule, group) -> results
for p in U:
    modes = [("fee5000", 5000)] if p["line"] == "2.433" else [("fee10000", 10000)]
    if p["line"] == "2.433": modes.append(("fee2500", 2500))
    for mode, fo in modes:
        for q in QS:
            for lag in (2, 1):
                if lag == 1 and q != 0.0058: continue
                if mode == "fee2500" and (q != 0.0058 or lag != 2): continue
                for name, r in run_pool(p, q, lag, fo).items():
                    RES[(p["line"], mode, q, lag, name, grp(p))].append(r)
                    RES[(p["line"], mode, q, lag, name, "ALL")].append(r)
                    if p["line"] == "3.0": RES[(p["line"], mode, q, lag, name, "old" if p["ts"] < NEW30 else "new")].append(r)
                    if p["line"] == "2.433" and p["day"] <= 5: RES[(p["line"], mode, q, lag, name, "d0-5")].append(r)
out = {}
lines = []
for k in sorted(RES, key=lambda k: (k[0], k[1], k[2], k[3], k[5], k[4])):
    rs = RES[k]; s = summ(rs, k[2]); s["no_trade_pulled_before_buy"] = sum(1 for r in rs if r["why"] == "pulled_before_buy")
    out["|".join(map(str, k))] = s
    lines.append(f"{k[0]:5s} {k[1]:8s} q{k[2]:<6} T+{k[3]} {k[5]:7s} {k[4]:12s} n {s['n']:4d} mean {s.get('mean%',0):+7.2f}% med {s.get('med%',0):+7.2f}% win {s.get('win',0):.3f} worst {s.get('worst%',0):+7.1f}% pulled {s.get('pulled',0):4d} ({s.get('pulled%',0):5.1f}%) $/tr {s.get('usd_tr',0):+.4f} nobuy(pulled<B) {s['no_trade_pulled_before_buy']}")
json.dump(out, open("r07_census_replay.json", "w"), indent=0)
open("r07_census_replay.txt", "w").write("\n".join(lines) + "\n")
for l in lines:
    if (" q0.0058 T+2 " in l) and ("fee2500" not in l): print(l)
