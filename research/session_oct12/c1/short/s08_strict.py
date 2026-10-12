"""The strict regime (offline, s04_exits.json): a position held from about our entry (ours, or an outsider's >= 0.001 ETH buy at or before T+5
that was still held), all T and T <= 100 (trigger max_blocks 100). Per pool and summary for the short exits; EV at $5 / $13 (gas $0.02)."""
from groups import *
import random
X = json.load(open(S("s04_exits.json"))); R = X["rows"]
STRICT = lambda r: r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")
EX = ["hold 10", "hold 20", "hold 25", "hold 30", "hold 40", "hold 60", "tp 3% cap 30", "tp 6% cap 40", "tp 6% cap 45", "tp 6% cap 50"]
def boot(v, B=10000, seed=5):
    rnd = random.Random(seed); n = len(v); ms = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B)); return ms[int(.025 * B)], ms[int(.975 * B)]
for nm, f in (("all T (max_blocks 400)", lambda r: True), ("T <= 100 (max_blocks 100)", lambda r: r["T"] <= 100)):
    g = [r for r in R if STRICT(r) and f(r)]
    print(f"== strict regime, {nm}: n {len(g)}: " + ", ".join(f"{r['pid'][:10]} T{r['T']} ({r['group']})" for r in g))
    for e in EX:
        a = [r["res"]["T 0.002"][e] for r in g]; b = [r["res"]["T 0.0058"][e] for r in g]
        lo, hi = boot(a); lo2, hi2 = boot(b)
        print(f"  {e:14s} mean {sum(a) / len(a):+6.2%} pulled {sum(1 for x in a if x <= -1)}/{len(a)} per pool [{', '.join('-100%' if x <= -1 else f'{x:+.1%}' for x in a)}]"
              f" | EV $5 {5 * sum(a) / len(a) - .02:+.3f} [{5 * lo - .02:+.3f}, {5 * hi - .02:+.3f}]  $13 {13 * sum(b) / len(b) - .02:+.3f} [{13 * lo2 - .02:+.3f}, {13 * hi2 - .02:+.3f}]")
