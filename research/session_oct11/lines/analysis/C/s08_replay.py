"""Replay the brief's rules on every studied V2/V3 family. Days are 24-h windows from the census start (d0 = Oct 4 13:52 .. d6 = the last
24 h, Oct 10 13:52 - Oct 11 13:52). Output: s08_replay.out (tables) and replay_results.pkl."""
import sys, os, pickle, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
T0 = 1791121962; DAYS = 7
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
Q = float(os.environ.get("Q_ETH", "0.0058"))
def day(r): return min(DAYS - 1, int((r["launch_ts"] - T0) // 86400))
def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None

def rules(r):
    """rule name -> (a, b) or None (rule not applicable to this pool)"""
    lo = r["liq_off"]
    if lo is None: return {}
    fr = r["frb"]["off"] if r["frb"] else None
    af = lo + 2
    out = {}
    out["front a=liq+2 b=frb+1"] = (af, fr + 1) if fr is not None and fr >= af else None
    for b in (10, 20, 40, 60, 100, 200, 300):
        out[f"front a=liq+2 b={b}"] = (af, b) if b > af else None
    out["front a=liq+2 b=a+60"] = (af, af + 60)
    if lo == 0:
        out["front a=1 b=frb+1"] = (1, fr + 1) if fr is not None and fr >= 1 else None
        for b in (10, 40, 60):
            out[f"front a=1 b={b}"] = (1, b)
    for k in (2, 4, 6):
        out[f"delayed oracle a=frb-{k} b=a+60"] = (fr - k, fr - k + 60) if fr is not None and fr - k >= af else None
    out["follow a=frb+2 b=a+20"] = (fr + 2, fr + 22) if fr is not None else None
    out["follow a=frb+2 b=a+60"] = (fr + 2, fr + 62) if fr is not None else None
    return out

RES = {}
lines = []
for name, rs in FP.items():
    n_fam = len(rs)
    if n_fam == 0: continue
    per_rule = defaultdict(list)
    for r in rs:
        o = E[r["pool"]]
        for rule, ab in rules(r).items():
            if ab is None: continue
            x = replay(r, o, ab[0], ab[1], Q)
            if x["ok"]:
                x["day"] = day(r); x["pool"] = r["pool"]; per_rule[rule].append(x)
    RES[name] = per_rule
    lines.append(f"\n### {name}: {n_fam} V2/V3 launches ({n_fam / 7:.1f}/day), q = {Q} ETH")
    lines.append("rule | n (share of launches) | mean | median | win | worst | pulled<=sell | $/trade | $/day | per-day mean (n) d0..d6 [d6 = last 24h]")
    for rule, xs in per_rule.items():
        if not xs: continue
        rets = [x["ret"] for x in xs]; usd = [x["usd"] for x in xs]
        share = len(xs) / n_fam
        pd = []
        for d in range(DAYS):
            ys = [x["ret"] for x in xs if x["day"] == d]
            pd.append(f"{st.mean(ys)*100:+.1f}%({len(ys)})" if ys else "-")
        lines.append(f"{rule} | {len(xs)} ({share:.2f}) | {st.mean(rets)*100:+.1f}% | {st.median(rets)*100:+.1f}% | {sum(1 for v in rets if v > 0)/len(rets):.2f} | {min(rets)*100:+.0f}% | {sum(1 for x in xs if x['pulled'])/len(xs):.3f} | {st.mean(usd):+.3f} | {st.mean(usd) * n_fam / 7 * share:+.1f} | " + " ".join(pd))
open(os.path.join(OUT, f"s08_replay{'_q'+str(Q) if Q != 0.0058 else ''}.out"), "w").write("\n".join(lines) + "\n")
pickle.dump(RES, open(os.path.join(OUT, f"replay_results{'_q'+str(Q) if Q != 0.0058 else ''}.pkl"), "wb"))
print("\n".join(lines))
