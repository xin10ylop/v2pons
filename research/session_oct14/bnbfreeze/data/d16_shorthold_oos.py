"""d16: the short hold (h = 3 blocks, under the shortest freeze seen) fitted on the first day of d12's pools and tested on the second:
the entry K in +40..+300 with the best mean on day 1, its mean/median/win on day 2, per tier. -> d16_shorthold_oos.out"""
import os, sys
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
src = open(os.path.join(D, "d12_reprice.py")).read().split("out = {\"n_pools\"")[0]
g = {"__file__": os.path.join(D, "d12_reprice.py")}; exec(compile(src, "d12_head", "exec"), g)
LS, replay, GAS = g["LS"], g["replay"], g["GAS"]
mid = (min(o["L"] for o in LS) + max(o["L"] for o in LS)) // 2
for size in (1.0, 10.0, 25.0):
    for h in (2, 3):
        a = [o for o in LS if o["size"] == size and o["L"] < mid]; b = [o for o in LS if o["size"] == size and o["L"] >= mid]
        def m(pools, K):
            xs = [(r[2] - r[0] - GAS) / r[0] for r in (replay(o, K, K + h) for o in pools) if r]
            xs.sort(); return sum(xs) / len(xs), xs[len(xs) // 2], sum(1 for x in xs if x > 0) / len(xs), len(xs)
        fit = max(range(40, 301), key=lambda K: m(a, K)[0])
        fa, fb = m(a, fit), m(b, fit)
        print("size %4s h %d: fitted K +%d on day 1 (n %d mean %+.2f%%) -> day 2 n %d mean %+.2f%% median %+.2f%% win %.0f%%" % (size, h, fit, fa[3], 100 * fa[0], fb[3], 100 * fb[0], 100 * fb[1], 100 * fb[2]))
