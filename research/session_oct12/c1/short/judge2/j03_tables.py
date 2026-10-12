"""Judge 2, step 3: $ per attempt at $5 (0.002 ETH at $2,500) for each exit, engine-exact (j02_sim.json), by trigger max_blocks (400: the box;
100) and regime, with pool-bootstrap 95% CIs (10,000 resamples). Gas from our own receipts (skeptic 2's k01_gas.out, re-read from the 16
receipts listed there): a filled round trip 4.317e-6 ETH, a fill whose sell met the pull 8.823e-6 ETH, a reverted attempt 1.820e-6 ETH.
Scenarios: base = buy at T+2, sell lag 2 (6 of our 7 sells); worst = T+3, lag 3; mix = T+2 75% / T+3 12.5% / T+7 12.5% (the 20:59 revert),
lag 1/2/3 at 15/70/15% (T+7 at lag 2)."""
from jc import *
import random, collections
X = json.load(open(JD("j02_sim.json"))); R = X["rows"]; EX = X["exits"]
USD = 2500.0; STK = 0.002; G_OK = 4.317e-6; G_PULL = 8.823e-6; G_REV = 1.820e-6
MIX = {"2|1": .75 * .15, "2|2": .75 * .70, "2|3": .75 * .15, "3|1": .125 * .15, "3|2": .125 * .70, "3|3": .125 * .15, "7|2": .125}
SHOW = ["hold 10", "hold 15", "hold 20", "hold 25", "hold 30", "hold 35", "hold 40", "hold 60", "tp 4% cap 30", "tp 6% cap 30", "tp 4% cap 40", "tp 6% cap 40"]


def usd(x, e):
    """$ of one attempt under one scenario, and (filled, gross, pulled, same-block)"""
    if not x["fill"]: return -G_REV * USD, (False, None, False, False)
    g, pulled, send, landoff, why, same = x["res"][e]
    return (STK * g - (G_PULL if pulled else G_OK)) * USD, (True, g, pulled, same)


def per_pool(r, e, sc):
    if sc == "mix":
        return sum(w * usd(r["sc"][k], e)[0] for k, w in MIX.items())
    return usd(r["sc"][sc], e)[0]


def boot(v, n=10000, seed=7):
    rnd = random.Random(seed); m = len(v)
    if m == 0: return (None, None)
    s = sorted(sum(v[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return s[int(.025 * n)], s[int(.975 * n) - 1]


def regimes(rows, mb):
    rr = [r for r in rows if r["T"] <= mb]
    return {"holder regime (ours + holders + bd13)": [r for r in rr if r["group"] in ("ours", "holder") or r["bd13"]],
            "held from T+2 (ours + early holders)": [r for r in rr if r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")],
            "all triggered": rr}


if __name__ == "__main__":
    out = {}
    for mb in (400, 100):
        for name, rows in regimes(R, mb).items():
            print(f"\n=== trigger max_blocks {mb} | {name}: {len(rows)} attempts")
            print(f"  {'exit':14s} | base T+2 lag 2: fills, pulled (same-block), mean gross of fills, EV $/attempt [95% CI] | mix: EV [CI] | worst T+3 lag 3: pulled, EV [CI]")
            for e in SHOW:
                line = f"  {e:14s} |"
                for sc in ("2|2", "mix", "3|3"):
                    v = [per_pool(r, e, sc) for r in rows]; lo, hi = boot(v); ev = sum(v) / len(v)
                    out[f"{mb}|{name}|{e}|{sc}"] = (ev, lo, hi)
                    if sc == "mix":
                        line += f" {ev:+.3f} [{lo:+.3f}, {hi:+.3f}] |"; continue
                    info = [usd(r["sc"][sc], e)[1] for r in rows]
                    f = [i for i in info if i[0]]; pl = sum(i[2] for i in f); same = sum(i[3] for i in f)
                    mg = sum(i[1] for i in f) / len(f) if f else float("nan")
                    if sc == "2|2":
                        line += f" {len(f)}/{len(rows)}, {pl} ({same}), {mg:+.2%}, {ev:+.3f} [{lo:+.3f}, {hi:+.3f}] |"
                    else:
                        line += f" {pl}, {ev:+.3f} [{lo:+.3f}, {hi:+.3f}]"
                print(line)
    json.dump(out, open(JD("j03_tables.json"), "w"))
    # per pool detail in the holder regime, max_blocks 400, base scenario
    print("\n=== holder regime per pool (max_blocks 400; base T+2 lag 2): gross per exit, the pull's offset from our buy")
    for r in regimes(R, 400)["holder regime (ours + holders + bd13)"]:
        x = r["sc"]["2|2"]
        hb = r["holder_buy"]
        tag = f"{r['group']}{'/' + r['sub'] if r['sub'] else ''}{' bd13' if r['bd13'] else ''}"
        if not x["fill"]:
            print(f"  {utc(r['ts'])} {r['pid'][:10]} T+{r['T']:<4d} {tag:18s} REVERT ({x['why']} {x.get('short', 0):+.2%}); pull T+{(r['pull'] - r['T']) if r['pull'] is not None else None}"); continue
        gs = " ".join(f"{x['res'][e][0] * 100:+6.1f}" for e in ("hold 10", "hold 20", "hold 25", "hold 30", "hold 35", "hold 60", "tp 4% cap 30", "tp 4% cap 40"))
        print(f"  {utc(r['ts'])} {r['pid'][:10]} T+{r['T']:<4d} {tag:18s} h10/20/25/30/35/60 tp4c30 tp4c40: {gs} | pull buy+{x['pull_after_buy']}"
              + (f" | holder buy T{hb['off'] - r['T']:+d} {hb['eth']:.4f} {hb['from'][:10]}" if hb else ""))
