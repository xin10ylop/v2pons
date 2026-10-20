"""the ranked top-15 table for REPORT.md (numbers from g08_detail.json)"""
from common import *
D = json.load(open(os.path.join(G, "g08_detail.json")))
def P(x): return "-" if x is None else f"{x*100:+.1f}%"
print("| # | family | /day (48 h) | rule | slices + / >=3 | val n | val mean | val med | win | worst | pulled | val $/day | all 7 d mean | last 24 h mean (n) | W: day-7 pick, mean | F: fit-only pick, val mean | q 0.002 val mean, $/day | K=0 bound |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for i, d in enumerate(D):
    V = d["V"]; v = V["val"]; a = V["all"]; l = V["last24"]; W = d["W"]; F = d["F"]
    q2 = d.get("V_q0.002_val") or {}
    print(f"| {i+1} | {d['fam'].split('=')[0]} {d['fam'].split('=')[1][:60]} | {d['per_day48']:.1f} | {V['rule']} | {V['slices_all'][1]}/{V['slices_all'][0]} | {v['n']} | {P(v['mean'])} | {P(v['median'])} | {v['win']:.0%} | {P(v['worst'])} | {v['pulled']:.1%} | {V['val_usd_day']:.0f} | {P(a['mean'])} | {P(l.get('mean'))} ({l['n']}) | "
          f"{W['rule'] if W else '-'}: {P(W['last24'].get('mean')) if W else '-'} | {F['rule'] if F else 'none'}: {P(F['val'].get('mean')) if F else '-'} | {P(q2.get('mean'))}, {d.get('V_q0.002_val_usd_day') or 0:.0f} | {P(V['k0_bound'].get('mean'))} |")
