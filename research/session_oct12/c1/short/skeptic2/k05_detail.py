"""Skeptic 2: per-pool detail of the regime under the engine's real execution (offline, k02_exec.json): every regime pool, fill or revert
(and why), the pull's block after our buy, the margin between the hold's sell and the pull, hold 20/25/30, tp 4% cap 30, tp 6% cap 50; the
leave-one-pool-out range of the regime's EV at $5 and $13 (does one pool carry it?); and the analyst's headline numbers re-derived."""
from sk import *
X = json.load(open(K("k02_exec.json"))); R = X["rows"]; G = json.load(open(K("k01_gas.json")))
GF, GP, GR = G["per_fill_wei"] / 1e18, G["per_pulled_wei"] / 1e18, G["per_revert_wei"] / 1e18
USD = {"0.002": 5.0, "0.0058": 13.0}; ETHUSD = {"0.002": 2500.0, "0.0058": 13.0 / 0.0058}
WB = ((2, .75), (3, .25)); WL = ((1, .25), (2, .5), (3, .25))
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]
EXACT = lambda r: r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")
def usd(x, e, stake):
    if not x["fill"]: return -GR * ETHUSD[stake]
    g, pulled, _ = x["res"][e]; return USD[stake] * g - (GP if pulled else GF) * ETHUSD[stake]
def mix(r, e, stake): return sum(a * b * usd(r["sc"][f"{stake}|{dB}|top|{lag}"], e, stake) for dB, a in WB for lag, b in WL)
EX = ["hold 10", "hold 20", "hold 25", "hold 30", "tp 4% cap 30", "tp 6% cap 50", "hold 60"]
print("regime pools under the REAL execution (0.002, buy top of T+2, minOut 3%, sell lag 2): gross per exit; 'margin' = the pull's block minus hold 30's landing")
f = lambda x: "-100%" if x[1] else f"{x[0]:+.1%}"
for r in R:
    if not REG(r): continue
    x = r["sc"]["0.002|2|top|2"]
    tag = f"{r['group']:6s} {r['sub'] or '':5s} {'bd13' if r['bd13'] else '    '} {'EXACT' if EXACT(r) else '     '}"
    if not x["fill"]:
        print(f"  {utc(r['ts'])} {r['pid'][:10]} {tag} T {r['T']:3d} pull T+{r['pull_T']}: REVERT ({x['why']}{', ' + format(x['short'], '+.2%') if 'short' in x else ''})"); continue
    pab = x["pull_after_buy"]; margin = None if pab is None else pab - 32
    print(f"  {utc(r['ts'])} {r['pid'][:10]} {tag} T {r['T']:3d} pull at buy+{pab} (margin {margin}) | " + "  ".join(f"{e}: {f(x['res'][e])}" for e in EX))
for nm, pr in (("holder regime", REG), ("held from T+2", EXACT)):
    g = [r for r in R if pr(r)]
    print(f"\n{nm} (n {len(g)}): mixture EV $ per attempt, all pools / leave-one-pool-out min..max")
    for e in EX:
        for stake in ("0.002", "0.0058"):
            v = [mix(r, e, stake) for r in g]; m = sum(v) / len(v)
            loo = [(sum(v) - v[i]) / (len(v) - 1) for i in range(len(v))]
            print(f"  {e:13s} ${USD[stake]:.0f}: {m:+.3f}  LOO {min(loo):+.3f}..{max(loo):+.3f}", end="   ")
        print()
# per fill (not per attempt): the trade the engine actually makes
print("\nper FILLED trade (the engine's own P&L line), mixture, holder regime / held from T+2 / all usable:")
for nm, pr in (("regime", REG), ("exact", EXACT), ("all", lambda r: True)):
    g = [r for r in R if pr(r)]
    for e in ("hold 20", "hold 25", "hold 30", "tp 4% cap 30"):
        cells = []
        for stake in ("0.002", "0.0058"):
            num = den = 0.0
            for r in g:
                for dB, a in WB:
                    for lag, b in WL:
                        x = r["sc"][f"{stake}|{dB}|top|{lag}"]
                        if x["fill"]: num += a * b * usd(x, e, stake); den += a * b
            cells.append(f"${USD[stake]:.0f}: {num / den:+.3f} per fill over {den:.1f} fills")
        print(f"  {nm:6s} {e:13s} " + "   ".join(cells))
