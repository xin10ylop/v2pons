"""(2) the reaction as a rate, free of the 'the later the crowd, the more time for outsiders' bias: per block of pool age, while the crowd
has not come and the pool is not pulled, is an outside holder (>= 0.0005 ETH bought, less than half sold) on the pool? Rates of the crowd's
first real buy and of the pull, per 1,000 pool-blocks, with and without a holder, by age band; Mantel-Haenszel rate ratios across launch day x age band strata
(Greenland-Robins 95% CI). Then the same-age test: for each outside holder's first buy at age o, the pull and the crowd within N blocks,
observed against expected from every pool at risk at the same age."""
from rlib import *
import math
P = load(); BOT1 = "0x776e5a2a"
SINCE = os.environ.get("SINCE")          # e.g. 2026-10-08: only launches from that UTC day on
if SINCE:
    import calendar
    t0 = calendar.timegm(time.strptime(SINCE, "%Y-%m-%d")); P = [p for p in P if p["ts"] >= t0]
    print(f"launches from {SINCE} UTC on: {len(P)} pools")
BANDS = [(1, 20), (20, 40), (40, 60), (60, 80), (80, 120), (120, 200), (200, 400), (400, 800), (800, 3001)]
def intervals(p, sel):
    """holding intervals [a, b) of the selected outsiders"""
    iv = []
    for o in p["outs"]:
        if not sel(o): continue
        b = o["exit_off"] if o["exit_off"] is not None else 10 ** 9
        if b > o["first_off"]: iv.append((o["first_off"], b))
    return iv
def run(lab, sel):
    E = {b: [0, 0] for b in BANDS}; C = {b: [0, 0] for b in BANDS}; Pn = {b: [0, 0] for b in BANDS}
    import collections
    SE = collections.defaultdict(lambda: [0, 0]); SC = collections.defaultdict(lambda: [0, 0]); SP = collections.defaultdict(lambda: [0, 0])
    for p in P:
        stop = min(x for x in (p["frb"], p["pull"], p["end"]) if x is not None)
        iv = intervals(p, sel)
        excl = intervals(p, lambda o: not sel(o))       # blocks where only a non-selected outsider holds are left out of the 'without' side
        for t in range(1, min(stop, 3000) + 1):
            h = 1 if any(a <= t < b for a, b in iv) else 0
            if not h and any(a <= t < b for a, b in excl): continue
            band = next(b for b in BANDS if b[0] <= t < b[1]); day = time.strftime("%m-%d", time.gmtime(p["ts"]))
            E[band][h] += 1; SE[(day, band)][h] += 1
            if p["frb"] == t and (p["pull"] is None or p["pull"] >= t): C[band][h] += 1; SC[(day, band)][h] += 1
            if p["pull"] == t and (p["frb"] is None or p["frb"] > t): Pn[band][h] += 1; SP[(day, band)][h] += 1
    print(f"\n{lab}")
    print(f"  {'age band':>10} {'blocks w/o':>10} {'w/ holder':>9} | {'crowd w/o':>9} {'w/':>4} {'rate/1k w/o':>11} {'w/':>6} | {'pull w/o':>8} {'w/':>4} {'rate/1k w/o':>11} {'w/':>6}")
    for b in BANDS:
        e0, e1 = E[b]; c0, c1 = C[b]; q0, q1 = Pn[b]
        r = lambda k, e: f"{1000 * k / e:.2f}" if e else "-"
        print(f"  {str(b):>10} {e0:>10} {e1:>9} | {c0:>9} {c1:>4} {r(c0, e0):>11} {r(c1, e1):>6} | {q0:>8} {q1:>4} {r(q0, e0):>11} {r(q1, e1):>6}")
    for nm, D in (("crowd's first real buy", SC), ("pull before the crowd", SP)):
        num = den = 0.0; vs = 0.0; d1t = d0t = 0
        for b in SE:
            e0, e1 = SE[b]; d0, d1 = D[b]; T = e0 + e1
            if not T or (d0 + d1) == 0: continue
            num += d1 * e0 / T; den += d0 * e1 / T; d1t += d1; d0t += d0
            vs += (d0 + d1) * e1 * e0 / T ** 2        # Greenland-Robins variance for person-time
        if num == 0 or den == 0:
            print(f"  {nm}: MH rate ratio holder/no-holder: events with holder {d1t}, without {d0t}: no estimate"); continue
        rr = num / den; se = math.sqrt(vs / (num * den))
        print(f"  {nm}: MH rate ratio (holder / none; strata launch day x age band) {rr:.2f}  95% CI {rr * math.exp(-1.96 * se):.2f}-{rr * math.exp(1.96 * se):.2f}  (events with holder {d1t}, without {d0t})")
    return E, C, Pn
run("any outside holder (>= 0.0005 ETH)", lambda o: True)
run("outside holder that is not the +1 bot", lambda o: not o["w"].startswith(BOT1))
run("the +1 bot holding", lambda o: o["w"].startswith(BOT1))
run("outside holder >= 0.001 ETH, not the +1 bot (our size)", lambda o: not o["w"].startswith(BOT1) and o["eth_pre"] >= 0.001)
# same-age test
print("\nsame-age test: each outside holder's first buy (>= 0.0005 ETH, before the crowd, pool not pulled) at age o; observed vs expected"
      " over pools at risk at age o (no crowd, not pulled, observed to o + N), any pool")
def risk(o, N):
    """expected P(pull in (o, o+N] before the crowd), P(crowd in (o, o+N]) among pools at risk at o (crowd not yet, not pulled, observed)"""
    at = [p for p in P if (p["frb"] is None or p["frb"] > o) and (p["pull"] is None or p["pull"] > o) and p["end"] >= min(o + N, p["pull"] or 10 ** 9)]
    if not at: return None
    pp = sum(1 for p in at if p["pull"] is not None and p["pull"] <= o + N and (p["frb"] is None or p["frb"] > p["pull"])) / len(at)
    pc = sum(1 for p in at if p["frb"] is not None and p["frb"] <= o + N) / len(at)
    return pp, pc, len(at)
cache = {}
def poisson_ci(k):
    """exact 95% CI for a Poisson count (the cdf in log space, bisection)"""
    from math import lgamma, log, exp
    def cdf(m, k):
        if k < 0: return 0.0
        if m <= 0: return 1.0
        ls = [-m + i * log(m) - lgamma(i + 1) for i in range(k + 1)]; mx = max(ls)
        return exp(mx) * sum(exp(v - mx) for v in ls)
    def solve(f, lo, hi):
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid): lo = mid
            else: hi = mid
        return (lo + hi) / 2
    lo = 0.0 if k == 0 else solve(lambda m: 1 - cdf(m, k - 1) < 0.025, 0, k * 3 + 50)
    hi = solve(lambda m: cdf(m, k) > 0.025, 0, k * 3 + 50)
    return lo, hi
for lab, sel in (("not the +1 bot", lambda o: not o["w"].startswith(BOT1)), ("the +1 bot", lambda o: o["w"].startswith(BOT1)),
                 ("not the bot, first buy at +1..+10", lambda o: not o["w"].startswith(BOT1) and o["first_off"] <= 10),
                 ("not the bot, >= 0.001 ETH", lambda o: not o["w"].startswith(BOT1) and o["eth_pre"] >= 0.001)):
    for N in (36, 62, 78, 120, 200):
        Op = Ep = Oc = Ec = 0; n = 0
        for p in P:
            seen = set()
            for o in p["outs"]:
                if not sel(o): continue
                t = o["first_off"]
                if t in seen: continue
                seen.add(t)
                if (p["frb"] is not None and p["frb"] <= t) or (p["pull"] is not None and p["pull"] <= t): continue
                if p["end"] < min(t + N, p["pull"] or 10 ** 9): continue
                k = (t, N)
                if k not in cache: cache[k] = risk(t, N)
                if not cache[k]: continue
                pp, pc, _ = cache[k]; n += 1; Ep += pp; Ec += pc
                Op += p["pull"] is not None and p["pull"] <= t + N and (p["frb"] is None or p["frb"] > p["pull"])
                Oc += p["frb"] is not None and p["frb"] <= t + N
        lp, hp = poisson_ci(Op); lc, hc = poisson_ci(Oc)
        print(f"  {lab:<36} N {N:>3}: buys {n:>4}  pull before crowd obs {Op:>3} exp {Ep:6.1f} (O/E {Op / Ep if Ep else float('nan'):.2f}, 95% {lp / Ep if Ep else 0:.2f}-{hp / Ep if Ep else 0:.2f})"
              f"   crowd obs {Oc:>4} exp {Ec:6.1f} (O/E {Oc / Ec if Ec else float('nan'):.2f}, 95% {lc / Ec if Ec else 0:.2f}-{hc / Ec if Ec else 0:.2f})")
