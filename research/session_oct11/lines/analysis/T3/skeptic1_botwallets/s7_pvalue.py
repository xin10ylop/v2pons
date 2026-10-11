"""Stage 7: is the count of pools with a bot-wallet tx in d 1..4 above what the background rate predicts? One-sided binomial tail
P(X >= observed | n pools, p = 1-(1-bg)^4), from the s4_rule.out figures (cur+late, both wallet sets; old regime for reference)."""
from math import comb
def tail(n, k, p): return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k, n + 1))
for label, n, k, bg in (("cur+late, W union (216), ANY", 121, None, None),):
    pass
import re
txt = open("s4_rule.out").read().split("######## wallet set ")
for sec in txt[1:]:
    wname = sec.split("\n")[0]
    for reg in re.split(r"\n== regime ", sec)[1:]:
        rname = reg.split(":")[0]
        for line in reg.split("\n"):
            m = re.search(r"^\s+(ANY bot-wallet tx|bot buy \(another pool\)|bot-wallet sell via UR 24856bc3|bot-wallet other tx)\s.*bg/blk\s+([\d.]+)% \| any in d1-4 (\d+)/(\d+)", line)
            if m:
                c, bg, k, n = m.group(1), float(m.group(2)) / 100, int(m.group(3)), int(m.group(4))
                p4 = 1 - (1 - bg) ** 4
                print(f"{wname[:28]:28s} {rname:9s} {c:32s} observed {k:3d}/{n:3d}  expected {n*p4:6.1f}  ratio {k/(n*p4) if p4 else 0:4.2f}  P(X>=obs) {tail(n, k, p4):.3f}")
