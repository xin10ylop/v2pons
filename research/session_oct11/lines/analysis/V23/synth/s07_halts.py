"""Synthesizer step 7: per-line halt thresholds for a 40-trade $5 probe on the statistic of s06 (share of our trades with a real buy inside
the hold; census shares below). Threshold k = the largest count whose binomial lower tail under the census share is <= 2% (a false halt
at most 2% of the time); also the chance of passing if that share halved. -> s07_halts.out"""
from math import comb
import os
HERE = os.path.dirname(os.path.abspath(__file__))
def tail_le(n, p, k): return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
# census shares from s06_window_buys.out (all 7 days) and, for 356-B, the pump share at/after +60 from s04_pumpgate356.out
CASES = [("V3 356-B: pumped at/after +60", 38, 111), ("V3 356-B: real buy inside the hold", 22, 111), ("V3 crowd: real buy inside the hold", 371, 1046),
         ("V2 fleet: real buy inside the hold", 252, 603), ("V2 70adce63 >= 40: real buy inside the hold", 918, 1029)]
L = []
for lab, a, n0 in CASES:
    p = a / n0; n = 40
    k = max(k for k in range(n + 1) if tail_le(n, p, k) <= 0.02)
    L.append(f"{lab}: census {a}/{n0} = {p*100:.1f}%; 40 trades expect {n*p:.1f}; halt if <= {k} (false halt {tail_le(n, p, k)*100:.1f}%; "
             f"if the share halved, halted {tail_le(n, p / 2, k)*100:.0f}% of the time)")
open(os.path.join(HERE, "s07_halts.out"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
