"""Local only: what a 100-trade $5 probe looks like if nothing reacts, from the replay's per-launch table (entry +2, sell landing +2).
0.002 ETH is interpolated between the 0.0012 and 0.0036 columns. Bootstrap of 100-trade sums (in $ at $2,520/ETH); then with one pull (-100%)."""
import csv, random, statistics as st, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "replay", "r12_launches.tsv")
rows = list(csv.DictReader(open(R), delimiter="\t"))
f = lambda s: float(s.strip().rstrip("%")) / 100
a = [f(r["net_0.0012_e2"]) for r in rows]; b = [f(r["net_0.0036_e2"]) for r in rows]
w = (0.002 - 0.0012) / (0.0036 - 0.0012); r2 = [x + w * (y - x) for x, y in zip(a, b)]
usd = 0.002 * 2520
print(f"n {len(r2)}  0.002 ETH (${usd:.2f}): mean {st.mean(r2):+.2%}  median {st.median(r2):+.2%}  win {sum(x > 0 for x in r2)}  $/trade mean {st.mean(r2)*usd:+.3f} median {st.median(r2)*usd:+.3f}")
s = sorted(r2, reverse=True); k = len(s) // 10
print(f"  without top 10% ({k}): {st.mean(s[k:]):+.2%}  top-10% share {sum(s[:k]) / sum(s):.0%}")
# by day
for d in ("10-10", "10-11", "10-12"):
    x = [v for v, r in zip(r2, rows) if r["launch_utc"].startswith(d)]
    print(f"  {d}: n {len(x)} mean {st.mean(x):+.2%} median {st.median(x):+.2%}")
random.seed(7); N = 100; sims = sorted(sum(random.choice(r2) for _ in range(N)) * usd for _ in range(20000))
q = lambda p: sims[int(p * len(sims))]
print(f"100-trade sum, no reaction: p5 {q(.05):+.2f}  p25 {q(.25):+.2f}  median {q(.5):+.2f}  p75 {q(.75):+.2f}  p95 {q(.95):+.2f}  P(<0) {sum(v < 0 for v in sims)/len(sims):.1%}")
# 30 trades
sims30 = sorted(sum(random.choice(r2) for _ in range(30)) * usd for _ in range(20000)); q3 = lambda p: sims30[int(p * len(sims30))]
print(f"30-trade sum: p5 {q3(.05):+.2f} median {q3(.5):+.2f} p95 {q3(.95):+.2f}  P(<0) {sum(v < 0 for v in sims30)/len(sims30):.1%}")
# crowd-clock exits in the replay (the probe's crowd signal)
ex = [r["exit(e2)"] for r in rows]; c = sum(e.startswith("crowd") for e in ex)
print(f"exits by the crowd's clock {c}/{len(ex)} ({c/len(ex):.0%}); others: {sorted(set(e for e in ex if not e.startswith('crowd')))[:5]}")
from math import comb
p = c / len(ex)
for n, kmax in ((30, 0), (30, 1), (50, 2), (50, 3)):
    print(f"  P(<= {kmax} crowd exits in {n} | p {p:.2f}) = {sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(kmax + 1)):.4f}")
