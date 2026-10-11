"""Synthesizer step 5: numbers for the $5 probe and the per-line halts. For each line's rule at q = $5 (0.001946 ETH), replayed in launch
order over the 7 census days (same replays as s02): the worst drawdown of cumulative $, the longest run of losing trades, the number of
-100% trades; for the 356-B line, how many pumped pools a 40-trade probe should see if our buy does not deter the pump (census pump
share at/after +60, s04) versus if it does (the share seen after an early outside buy), with the binomial tails for a halt threshold.
-> s05_probe.out"""
import sys, os, json, pickle, statistics as S
from math import comb
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "s02_lines.py")).read().split("# ---- overlaps")[0])      # loaders and keys only (no output)
src = open(os.path.join(HERE, "s02_lines.py")).read()
exec(src[src.index("def v3run"):src.index("def stats")])
L = []
def P(s=""): L.append(s); print(s)
Q5 = round(5 / ETH_USD, 6)
s2_ = {k: set(v) for k, v in F2.items()}; s3_ = {k: set(v) for k, v in F3.items()}
v40 = (s2_[SH + "50.0900000"] | s2_[SH + "40.0900000"] | s2_[SH + "40.5900000"]) & s2_[K_70]
LINES = [("V3 356-B K60 -> +260", v3run, sorted(s3_[K_356]), 60, 260), ("V3 crowd K20 -> +80", v3run, sorted(s3_[K_CROWD]), 20, 80),
         ("V2 fleet +20 -> +80", v2run, sorted(s2_[K_FLEET]), 20, 80), ("V2 70adce63 >= 40 ETH +150 -> +250", v2run, sorted(v40), 150, 250)]
for lab, fn, pools, a, b in LINES:
    xs = sorted(fn(pools, a, b, Q5), key=lambda x: x["ts"]); u = [x["ret"] * Q5 * ETH_USD for x in xs]
    cum = 0; peak = 0; dd = 0; run = 0; mrun = 0
    for v in u:
        cum += v; peak = max(peak, cum); dd = min(dd, cum - peak)
        run = run + 1 if v <= 0 else 0; mrun = max(mrun, run)
    first40 = []
    for i in range(0, len(u) - 39, 40): first40.append(sum(u[i:i + 40]))
    P(f"{lab} at $5: n {len(u)} total ${sum(u):.2f} | worst drawdown ${dd:.2f} | longest losing run {mrun} | -100% trades {sum(1 for x in xs if x['pulled'])} | "
      f"40-trade blocks: {len(first40)}, losing {sum(1 for s in first40 if s <= 0)}, worst ${min(first40):.2f}, median ${S.median(first40):.2f}")
def tail_le(n, p, k): return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
p_no, p_det = 38 / 111, 6 / 44          # s04: pumped at/after +60 in all 111; pumped after an early outside buy >= 0.0005 ETH
P(f"\n356-B probe: pump share {p_no*100:.1f}% (census) vs {p_det*100:.1f}% (after an early outside buy)")
for n in (20, 40):
    for k in range(2, 13):
        a1, a2 = tail_le(n, p_no, k), 1 - tail_le(n, p_det, k)
        if a1 <= 0.10 and a2 <= 0.25 or k in (n // 10,):
            P(f"   n {n}: halt if pumped <= {k}: false halt (no deterrence) {a1*100:.1f}% | missed deterrence {a2*100:.1f}%")
open(os.path.join(HERE, "s05_probe.out"), "w").write("\n".join(L) + "\n")
