"""Judge 2, step 9: the in-hold pull hazard by trigger window: a lognormal on the reaction lags of positions bought by T+150 in pools with
T <= 100 against all, P(lag <= landing) x P(a reaction pull | we hold) (4 of our 5 fills), and the probe's expected $ at that hazard."""
from j07_probe import *
if __name__ == "__main__":
    Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    for lab, sel in (("all T", lambda r: True), ("T <= 100", lambda r: r["T"] is not None and r["T"] <= 100), ("T > 100", lambda r: r["T"] is not None and r["T"] > 100)):
        lags = sorted(r["lag"] for r in RX if not r["late"] and r["buy_T"] is not None and sel(r))
        lg = [math.log(x) for x in lags]; mu = statistics.mean(lg); sd = statistics.stdev(lg)
        hz = {land: Phi((math.log(land + 0.5) - mu) / sd) * 0.8 for land in (27, 32, 33)}
        print(f"{lab:9s}: n {len(lags)}, lags {lags[:8]}..., lognormal mu {mu:.2f} sd {sd:.2f}; hazard at landing buy+27 {hz[27]:.4f}, +32 {hz[32]:.4f}, +33 {hz[33]:.4f}")
    for mb, q in ((100, None), (400, None)):
        lags = sorted(r["lag"] for r in RX if not r["late"] and r["buy_T"] is not None and (r["T"] <= 100 if mb == 100 else True))
        lg = [math.log(x) for x in lags]; mu = statistics.mean(lg); sd = statistics.stdev(lg)
        q = Phi((math.log(32.5) - mu) / sd) * 0.8 + (0.0 if mb == 100 else 1 / 182)    # + the pre-T-holder near miss (0xcf1d880b) for 400
        for name in ("holder regime (ours + holders + bd13)", "all triggered"):
            vals = pool_vals(regimes(R, mb)[name], "hold 30")
            a, m, ex, en, tot, pp = probe(vals, q); mm, p5, p50, p95, pl = mc(vals, q, sims=20000)
            print(f"mb {mb} {name[:13]:13s} hold 30 at hazard q {q:.4f}: $/attempt {ex:+.3f}, E[N] {en:.1f}, P(stopped by a pull) {pp:.2f}, E[probe $] {tot:+.2f}; MC 5% {p5:+.2f} 50% {p50:+.2f} 95% {p95:+.2f}, P(loss) {pl:.2f}")
