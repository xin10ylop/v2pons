"""Judge 1: the expected $ of a live probe run until 100 attempts or the first pull inside the hold (the engine's family halt), at $5.
Per attempt: a pool drawn from the engine-exact replay's attempts (b: all triggered pools of the setting; a: holder regime), its own fill or
revert and $ (j02_sim.usd). On a fill, with probability q the operator pulls before our sell lands (-$5 stake - the pulled sell's gas, then
the family halts). Scenarios: a flat hazard q, and an operator that adapts after k of our fills (its next pull lands inside our hold).
20,000 runs each. Also: the hazard the data allow (0 pulls in n fills), the break-even hazard, leave-one-out and top-pool dependence."""
from j02_sim import *
import random
pools, head = load_pools()
line = [p for p in pools if p["shape"] == "line"]
stake = 2 * 10 ** 15
HOLDER = ("ours", "holder-pre", "holder-early", "holder-later", "bd13")
PULL_USD = -(stake + G_PULLED) / 1e18 * ETHUSD
rnd = random.Random(7)
def mc(outs, q=0.0, k_adapt=None, n_att=100, runs=20000):
    tot = []; halted = 0; atts = []
    for _ in range(runs):
        s = 0.0; fills = 0; h = False
        for i in range(n_att):
            fill, v = outs[rnd.randrange(len(outs))]
            if fill:
                if (k_adapt is not None and fills >= k_adapt) or rnd.random() < q:
                    s += PULL_USD; h = True; atts.append(i + 1); break
                fills += 1
            s += v
        else: atts.append(n_att)
        tot.append(s); halted += h
    tot.sort()
    return sum(tot) / runs, halted / runs, sum(atts) / runs, tot[int(.05 * runs)], tot[int(.5 * runs)], tot[int(.95 * runs)], sum(1 for x in tot if x < 0) / runs
for mb, ex in ((100, "hold 30"), (100, "hold 25"), (400, "hold 30")):
    rows = run(line, stake, mb)
    for rn, f in (("(b) all triggered", lambda r: True), ("(a) holder regime", lambda r: r["reg"] in HOLDER)):
        R = [r for r in rows if f(r)]
        outs = [(r["fill"], usd(r, ex, stake)) for r in R]
        nf = sum(1 for o in outs if o[0]); m = sum(o[1] for o in outs) / len(outs); mfill = sum(o[1] for o in outs if o[0]) / nf
        fr = nf / len(outs); rev = -G_REV / 1e18 * ETHUSD
        qbe = (fr * mfill + (1 - fr) * rev) / (fr * (mfill - PULL_USD))
        cp = 1 - 0.05 ** (1 / nf)
        vals = sorted((usd(r, ex, stake), r["pid"][:10]) for r in R)
        loo = [(m * len(R) - v) / (len(R) - 1) for v, _ in vals]
        top3 = sum(v for v, _ in vals[-3:])
        print(f"\n== max_blocks {mb}, {ex}, {rn}: attempts {len(R)}, fill rate {fr:.0%}, $/attempt {m:+.3f} (per fill {mfill:+.3f}); break-even pull hazard per fill {qbe:.2%}; "
              f"data: 0 pulls in {nf} fills, one-sided 95% upper {cp:.1%}")
        print(f"   leave-one-out $/attempt {min(loo):+.3f}..{max(loo):+.3f}; top 3 pools {', '.join(f'{p} {v:+.2f}' for v, p in vals[-3:])} = {top3 / (m * len(R)):.0%} of the total; without them {(m * len(R) - top3) / (len(R) - 3):+.3f}")
        if rn.startswith("(a)") and mb == 400: continue
        print("   probe until 100 attempts or the first pull:   E[$]    P(halted)  E[attempts]   p5     p50     p95    P($<0)")
        for q in (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.10):
            r_ = mc(outs, q=q)
            print(f"     flat hazard q {q:5.1%}                      {r_[0]:+6.2f}   {r_[1]:6.1%}    {r_[2]:6.1f}     {r_[3]:+6.2f} {r_[4]:+6.2f} {r_[5]:+6.2f}   {r_[6]:.0%}")
        for k in (0, 5, 10, 25, 50):
            r_ = mc(outs, k_adapt=k)
            print(f"     adapts after {k:2d} of our fills              {r_[0]:+6.2f}   {r_[1]:6.1%}    {r_[2]:6.1f}     {r_[3]:+6.2f} {r_[4]:+6.2f} {r_[5]:+6.2f}   {r_[6]:.0%}")
print(f"\npull outcome {PULL_USD:+.3f} $; launches per day of the line: see j01 (208 line pools Oct 11 01:00 - Oct 12 14:14)")
D = json.load(open(JD("j01_pools.json")))
for mb in (100, 400):
    rows = run(line, stake, mb); ts = sorted(r["ts"] for r in rows)
    print(f"  max_blocks {mb}: {len(rows)} attempts over {(ts[-1] - ts[0]) / 3600:.1f} h = {len(rows) / ((ts[-1] - ts[0]) / 86400):.0f} a day; fills {sum(r['fill'] for r in rows)}")
    last = [r for r in rows if r["ts"] >= 1791813600]
    print(f"    since 14:00 UTC Oct 12 (line shape): " + "; ".join(f"{r['pid'][:10]} T+{r['T']} {'FILL ' + format(r['res']['hold 30'][0], '+.2%') if r['fill'] else 'rev'}" for r in last))
