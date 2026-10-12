"""Judge 2, step 7: robustness of the candidate exits and the expected $ of a live probe run until 100 attempts or the first pull in the hold
(the engine's family halt: _settle line 2008, HALTED.front.c1).

Per attempt (j02 replay, the mix scenario of j03): a = P(fill), m = mean $ of a fill not pulled, c = $ of a revert (gas), Lp = $ of a fill
pulled before our sell (-0.002 ETH stake - 8.823e-6 ETH gas, at $2,500). On top of what the replay saw (0 pulls at hold <= 30), a hazard q
per fill that the reaction lands before our sell. The probe stops at the first such pull (N = min(100, first pull)); by Wald's identity
E[sum] = E[N] x E[per attempt]. Also a Monte Carlo (pools resampled from the replay, q injected) for the spread.
q is unknown: 0 seen (0/23 regime fills, 0/134 all), the 95% upper bounds 12% / 2.2%; a lognormal fit to the 21 reaction lags on positions
bought by T+150 (j06) gives P(lag <= landing); the near miss 0xcf1d880b (a holder from T-140, pulled 17 blocks after our would-be entry; the
engine's buy reverts there only because a 0.28 ETH router buy in block T left it 2.4% short of minOut) is counted as one more hazard."""
from j03_tables import *
import math, statistics
RX = json.load(open(JD("j06_margin.json")))
STOP_PULL = (STK + G_PULL) * USD


def pool_vals(rows, e):
    """per pool: (P(fill), $ if filled and not pulled, $ if reverted) under the mix scenario"""
    out = []
    for r in rows:
        pf = 0.0; mf = 0.0; cr = 0.0
        for k, w in MIX.items():
            x = r["sc"][k]; v, info = usd(x, e)
            if info[0] and not info[2]: pf += w; mf += w * v
            elif info[0] and info[2]: pf += w; mf += w * v           # (a replay pull: kept as is)
            else: cr += w * v
        out.append((pf, mf / pf if pf else 0.0, cr / (1 - pf) if pf < 1 else -G_REV * USD))
    return out


def probe(vals, q, n=100):
    a = sum(v[0] for v in vals) / len(vals)
    m = sum(v[0] * v[1] for v in vals) / max(1e-12, sum(v[0] for v in vals))
    c = -G_REV * USD
    ex = a * (1 - q) * m + (1 - a) * c - a * q * STOP_PULL
    s = a * q
    en = n if s == 0 else (1 - (1 - s) ** n) / s
    return a, m, ex, en, en * ex, 1 - (1 - s) ** n


def mc(vals, q, n=100, sims=20000, seed=11):
    rnd = random.Random(seed); tot = []
    for _ in range(sims):
        t = 0.0
        for i in range(n):
            pf, mf, cr = vals[rnd.randrange(len(vals))]
            if rnd.random() < pf:
                if rnd.random() < q: t -= STOP_PULL; break
                t += mf
            else: t += cr
        tot.append(t)
    tot.sort()
    return sum(tot) / sims, tot[int(.05 * sims)], tot[int(.5 * sims)], tot[int(.95 * sims)], sum(x < 0 for x in tot) / sims


if __name__ == "__main__":
    # (1) leave-one-out and drop-the-best for the candidates
    print("(1) robustness, mix scenario, $ per attempt at $5")
    for mb in (400, 100):
        for name, rows in regimes(R, mb).items():
            if name.startswith("held"): continue
            for e in ("hold 25", "hold 30", "tp 4% cap 30"):
                v = [per_pool(r, e, "mix") for r in rows]; base = sum(v) / len(v)
                loo = [(sum(v) - v[i]) / (len(v) - 1) for i in range(len(v))]
                srt = sorted(v, reverse=True); drop3 = sum(srt[3:]) / (len(v) - 3)
                med = statistics.median(v)
                print(f"   max_blocks {mb} {name[:13]:13s} {e:13s}: {base:+.3f}; leave-one-out {min(loo):+.3f}..{max(loo):+.3f}; without the 3 best {drop3:+.3f}; median attempt {med:+.4f}; best 3 {[round(x, 3) for x in srt[:3]]}")
    # (2) the hazard q: a lognormal on the reaction lags of positions bought by T+150
    early = [r["lag"] for r in RX if not r["late"] and r["buy_T"] is not None]
    lg = [math.log(x) for x in early]; mu = statistics.mean(lg); sd = statistics.stdev(lg)
    Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    ours_react = 4 / 5
    print(f"\n(2) reaction lags on positions bought by T+150: n {len(early)}, median {statistics.median(early)}, lognormal mu {mu:.2f} sd {sd:.2f}")
    for land in (27, 32, 33, 37, 42):
        p = Phi((math.log(land + 0.5) - mu) / sd)
        print(f"   P(lag <= {land}) = {p:.4f}; x P(a reaction pull at all | we hold) {ours_react:.1f} = {p * ours_react:.4f}")
    # (3) the probe
    print("\n(3) live probe until 100 attempts or the first pull in the hold: E[$] = E[N] x E[$ per attempt]; Monte Carlo 5% / median / 95%, P(net loss)")
    for mb in (400, 100):
        for name, rows in regimes(R, mb).items():
            if name.startswith("held"): continue
            for e in ("hold 25", "hold 30"):
                vals = pool_vals(rows, e)
                for q in (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20):
                    a, m, ex, en, tot, ppull = probe(vals, q)
                    mm, p5, p50, p95, ploss = mc(vals, q, sims=4000)
                    print(f"   mb {mb} {name[:13]:13s} {e} q {q:4.1%}: fill {a:.2f}, $/fill {m:+.3f}, $/attempt {ex:+.3f}, E[N] {en:5.1f}, P(stopped by a pull) {ppull:.2f}, "
                          f"E[probe $] {tot:+.2f} (MC {mm:+.2f}; 5% {p5:+.2f}, 50% {p50:+.2f}, 95% {p95:+.2f}; P(loss) {ploss:.2f})")
                qs = (a * m + (1 - a) * (-G_REV * USD)) / (a * (m + STOP_PULL))
                print(f"     break-even q (per fill) {qs:.2%}")
    # (4) adaptation: the operator speeds its pull inside our hold after K of our exits beat it; the probe then ends on that trade
    print("\n(4) adaptation: q 1% until the operator answers after K filled exits (then the next fill is pulled): E[probe $]")
    for mb in (400, 100):
        vals = pool_vals(regimes(R, mb)["all triggered"], "hold 30")
        a, m, ex0, _, _, _ = probe(vals, 0.01)
        for K in (3, 5, 10, 20, 40):
            # expected attempts before the K-th fill ~ K / a; profit until then (q 1%), then one pulled stake
            rnd = random.Random(5); tot = []
            for _ in range(4000):
                t = 0.0; fills = 0
                for i in range(100):
                    pf, mf, cr = vals[rnd.randrange(len(vals))]
                    if rnd.random() < pf:
                        if fills >= K or rnd.random() < 0.01: t -= STOP_PULL; break
                        t += mf; fills += 1
                    else: t += cr
                tot.append(t)
            print(f"   mb {mb} hold 30, K {K:2d}: E[probe $] {sum(tot) / len(tot):+.2f}, P(loss) {sum(x < 0 for x in tot) / len(tot):.2f}")
