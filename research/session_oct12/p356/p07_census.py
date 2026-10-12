"""p07: census 2 (Oct 4 13:52 .. Oct 11 13:52 UTC; scratchpad cache, no network) for the same launcher code (lc:89885b75|d27d1e00, 248
launches): the rule buy +60 / sell +260 with the same replay (analysis/C/replay.py via common.trade), split into the 356-B value-0 launches
(the p356 line, 111 in REPORT_V23) and the value launches (the longer calls), plus the launch position's fingerprint from the census events.
-> p07_census.out, p07_census.json"""
import sys, os, json, pickle, statistics as S, collections as C
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as K
SCR = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2"
sys.path.insert(0, SCR + "/census")
from load import load_events
F = json.load(open(SCR + "/analysis/G3/opus/families.json"))
R = {r["pool"]: r for r in pickle.load(open(SCR + "/analysis/G3/opus/v3rows.pkl", "rb"))}
lc = F["lc=89885b75|d27d1e00"]
E = load_events(set(lc))
FROM_TS = 1791121962; FIT_END = FROM_TS + 5 * 86400
Q15, Q5 = 0.0058, round(5 / K.ETH_USD, 6)
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
P(f"census lc:89885b75|d27d1e00 launches {len(lc)}; with events {sum(1 for p in lc if p in E)}")
P("by (calldata length, value > 0): " + str(sorted(C.Counter((R[p]["launch"]["calldata_len"], int(R[p]["launch"]["value_wei"]) > 0) for p in lc).items())))
OUT = {}
groups = {"v0 356-B value 0": [p for p in lc if R[p]["launch"]["calldata_len"] == 356 and int(R[p]["launch"]["value_wei"]) == 0],
          "356-B with value": [p for p in lc if R[p]["launch"]["calldata_len"] == 356 and int(R[p]["launch"]["value_wei"]) > 0],
          "value launches (len != 356)": [p for p in lc if R[p]["launch"]["calldata_len"] != 356]}
for g, ps in groups.items():
    P(f"\n== {g}: n {len(ps)}; value ETH p10/50/90 " + "/".join(f"{sorted(int(R[p]['launch']['value_wei'])/1e18 for p in ps)[int(k*len(ps))]:.2f}" for k in (0.1, 0.5, 0.9)) if ps else "")
    fp = C.Counter()
    for p in ps:
        o = E[p]; ms = [e for e in o["ev"] if e[0] == "mi" and e[1] == o["lb"]]
        fp[(len(ms), tuple((m[6], m[7], m[8]) for m in ms[:1]))] += 1
    P("  launch-block mints (count, (lo, hi, L)): " + str(fp.most_common(4)))
    lt = [sum(1 for e in E[p]["ev"] if e[0] == "s" and e[1] == E[p]["lb"]) for p in ps]
    P(f"  swaps in the launch block: pools with any {sum(1 for v in lt if v)}; median count {S.median(lt) if lt else '-'}")
    for q, lab in ((Q15, "$15"), (Q5, "$5")):
        xs = []
        for p in ps:
            o = {"lb": R[p]["launch_block"], "ev_to": E[p]["ev_to"], "ev": E[p]["ev"]}
            x = {"pool": p}
            t = K.trade(x, o, 60, 260, q)
            if t and t.get("ok"): xs.append((R[p]["launch_ts"], t))
        if not xs: continue
        rt = [t["ret"] for _, t in xs]; val = [t["ret"] for ts, t in xs if ts >= FIT_END]; usd = q * K.ETH_USD
        o = {"n": len(rt), "mean": S.mean(rt), "median": S.median(rt), "win": sum(1 for a in rt if a > 0) / len(rt), "pulled": sum(t["pulled"] for _, t in xs) / len(rt),
             "usd_day7": sum(rt) * usd / 7, "val_n": len(val), "val_mean": S.mean(val) if val else None, "val_usd_day": sum(val) * usd / 2}
        OUT[f"{g} {lab}"] = o
        P(f"  rule +60/+260 {lab}: n {o['n']} mean {o['mean']*100:+.2f}% median {o['median']*100:+.3f}% win {o['win']*100:.1f}% pulled {o['pulled']*100:.1f}% "
          f"${o['usd_day7']:.1f}/day (7 d) | days 6-7 n {o['val_n']} " + (f"{o['val_mean']*100:+.2f}% ${o['val_usd_day']:.1f}/day" if val else "-"))
json.dump(OUT, open(K.J("p07_census.json"), "w"), indent=1)
open(K.J("p07_census.out"), "w").write("\n".join(L) + "\n")
