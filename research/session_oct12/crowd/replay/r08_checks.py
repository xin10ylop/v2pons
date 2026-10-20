"""Cross-checks of r06: (1) against REPORT_W's forward test (analysis/W/w05_recent_8h_forward.json: entry +2, sell at the head of
min(first real buy + 20, launch + 80), 0.0058 ETH, analyst C's float V3Sim; before gas): our 0.0058|2|2 is the same rule; (2) the engine's
dry pricing against the exact replay landing +1 (the dry price is the pool after every buy of the send block = a sell at the head of the
next block), per launch; (3) the top trades; (4) how far a 95-trade subset of the box's 24 h can move the mean."""
from common import *
import statistics as stt, random, calendar
D = json.load(open(J("r06_rows.json"))); R = D["rows"]; BF = D["base_fee"]; G = (D["gas"][0] + D["gas"][1]) * BF
Wf = json.load(open("/home/user/v2pons/research/session_oct11/lines/analysis/W/w05_recent_8h_forward.json"))
by = {r["pool"]: r for r in R}
print("== 1. vs REPORT_W's forward test (0.0058 ETH, before gas)")
d = []
for w in Wf:
    r = by.get(w["pool"])
    if r is None: print("  not in r06:", w["pool"], w["lb"]); continue
    m = r["r"]["0.0058|2|2"]; d.append((w["ret"], m["gross"], w["exit"], m["land_off"], w["pool"][:10]))
print(f"  {len(d)} launches in both; W mean {stt.mean(x[0] for x in d)*100:+.3f}%, ours {stt.mean(x[1] for x in d)*100:+.3f}%; exit block equal in {sum(1 for x in d if x[2] == x[3])}; "
      f"|diff| < 0.01 point in {sum(1 for x in d if abs(x[0] - x[1]) < 1e-4)}; max |diff| {max(abs(x[0] - x[1]) for x in d)*100:.4f} point")
for x in d:
    if abs(x[0] - x[1]) >= 1e-4 or x[2] != x[3]: print("   ", x)
print("\n== 2. the engine's dry pricing vs the exact replay landing +1 (same price point), per launch")
for q in (0.0058, 0.0012):
    diffs = [(r["dry"][str(q)]["dry"] - (r["r"][f"{q}|2|1"]["gross"] - 250_000 * BF / (q * 1e18)), r) for r in R]
    ds = [x[0] for x in diffs]
    print(f"  q {q}: dry - exact: mean {stt.mean(ds)*100:+.3f} point, median {stt.median(ds)*100:+.4f}, |d| < 0.1 point in {sum(1 for x in ds if abs(x) < 1e-3)}/{len(ds)}, "
          f"dry higher by > 1 point {sum(1 for x in ds if x > 0.01)}, lower by > 1 point {sum(1 for x in ds if x < -0.01)}; send block equal {sum(1 for x in diffs if x[1]['dry'][str(q)]['send_off'] == x[1]['r'][f'{q}|2|1']['send_off'])}")
    for x, r in sorted(diffs, key=lambda t: -abs(t[0]))[:6]:
        print(f"     {r['utc']} {r['pool'][:10]} dry {r['dry'][str(q)]['dry']*100:+.2f}% exact+1 {r['r'][f'{q}|2|1']['gross']*100:+.2f}% (send {r['dry'][str(q)]['send_off']} vs {r['r'][f'{q}|2|1']['send_off']}, {r['dry'][str(q)]['why']})")
print("\n== 3. the top 15 trades (0.0058|2|2, net)")
for r in sorted(R, key=lambda r: -r["r"]["0.0058|2|2"]["ret"])[:15]:
    m = r["r"]["0.0058|2|2"]
    print(f"   {r['utc']} {r['pool'][:10]} net {m['ret']*100:+7.2f}% (lands +1 {r['r']['0.0058|2|1']['ret']*100:+7.2f}%) trigger +{m['trig_off']} {m['trig_eth'] or 0:.4f} ETH, sold landing +{m['land_off']}, crowd's 1st +{r['crowd1_off']} "
          f"{(r['crowd1_to'] or '')[:10]}, pull +{r['burn_off']}, engine dry {r['dry']['0.0058']['dry']*100:+.2f}%")
print("\n== 4. the box's 24 h (Oct 11 14:23 - Oct 12 14:23 UTC): what a 95-of-n subset does to the dry mean")
t0, t1 = calendar.timegm((2026, 10, 11, 14, 23, 0)), calendar.timegm((2026, 10, 12, 14, 23, 0))
rs = [r for r in R if t0 <= r["ts"] < t1]; dv = [r["dry"]["0.0058"]["dry"] for r in rs]
random.seed(1); ms = sorted(stt.mean(random.sample(dv, 95)) for _ in range(20000))
print(f"  n {len(rs)}; dry mean {stt.mean(dv)*100:+.2f}%; random 95-subsets: p5 {ms[1000]*100:+.2f}% median {ms[10000]*100:+.2f}% p95 {ms[19000]*100:+.2f}%; P(mean >= +12.9%) {sum(1 for m in ms if m >= 0.129) / len(ms):.3f}")
print(f"  the subset without the {len(rs) - 95} flattest: {stt.mean(sorted(dv, key=abs)[len(rs) - 95:])*100:+.2f}%; dry > +9% in {sum(1 for x in dv if x > 0.09)}; the 3 biggest {[round(x * 100, 1) for x in sorted(dv)[-3:]]}")
print(f"  launches in the box's 24 h by 6 h: {[sum(1 for r in rs if t0 + 6 * 3600 * k <= r['ts'] < t0 + 6 * 3600 * (k + 1)) for k in range(4)]}; gaps between launches under 80 blocks (the dry slot): {sum(1 for a, b in zip(rs, rs[1:]) if b['lb'] - a['lb'] < 80)}")
