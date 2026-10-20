"""Skeptic 2: the tables (offline, k02_exec.json, k01_gas.json). Per regime, exit and execution scenario: attempts, fills, reverts, pulled,
the mean gross of the fills, and the expected $ per ATTEMPT (a reverted buy costs its gas, a fill pays stake x gross minus its own gas, a
fill whose sell meets the pull pays the 335k-gas sell too) at $5 (0.002 ETH, ETH $2,500) and $13 (0.0058 ETH, ETH $2,241), with 95% pool
bootstrap intervals (10,000 resamples). Regimes as the analyst's (recomputed in k02)."""
from sk import *
import random, collections, calendar
X = json.load(open(K("k02_exec.json"))); R = X["rows"]; G = json.load(open(K("k01_gas.json")))
GF, GP, GR = G["per_fill_wei"] / 1e18, G["per_pulled_wei"] / 1e18, G["per_revert_wei"] / 1e18
USD = {"0.002": 5.0, "0.0058": 13.0}; ETHUSD = {"0.002": 2500.0, "0.0058": 13.0 / 0.0058}
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]
EXACT = lambda r: r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")
NONE = lambda r: r["group"] == "none" and not r["bd13"]
GROUPS = [("holder regime (ours + holders + bd13)", REG), ("held from T+2 (ours + holders <= T+5)", EXACT), ("ours (5 fills)", lambda r: r["group"] == "ours"),
          ("holder later (> T+5)", lambda r: r["group"] == "holder" and r["sub"] == "later"), ("bd9dc5f6 from 13:15", lambda r: r["bd13"]), ("no holder", NONE)]

def outcome(r, sc, stake, e):
    """(fill?, gross or None, pulled?, $ of this attempt)"""
    x = r["sc"][f"{stake}|{sc}"]
    if not x["fill"]: return False, None, False, -GR * ETHUSD[stake]
    g, pulled, _ = x["res"][e]
    return True, g, pulled, USD[stake] * g - (GP if pulled else GF) * ETHUSD[stake]

def mix(r, stake, e, wB=((2, .75), (3, .25)), wL=((1, .25), (2, .5), (3, .25)), place="top"):
    """the expected $ of one attempt over the execution mixture (buy lands T+2 or T+3; the sell 1-3 blocks after it is sent)"""
    return sum(a * b * outcome(r, f"{dB}|{place}|{lag}", stake, e)[3] for dB, a in wB for lag, b in wL)

def boot(v, B=10000, seed=11):
    if not v: return (0, 0)
    rnd = random.Random(seed); n = len(v); ms = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return ms[int(.025 * B)], ms[int(.975 * B)]

def line(g, sc, e, stake="0.002"):
    o = [outcome(r, sc, stake, e) for r in g]
    fills = [x for x in o if x[0]]; gr = [x[1] for x in fills]
    usd = [x[3] for x in o]; lo, hi = boot(usd)
    return {"n": len(o), "fills": len(fills), "pulled": sum(1 for x in fills if x[2]), "mean_fill": sum(gr) / len(gr) if gr else None,
            "surv": (sum(x for x in gr if x > -1) / max(1, sum(1 for x in gr if x > -1))) if gr else None, "ev": sum(usd) / len(usd), "ci": (lo, hi)}

SHOW = ["hold 5", "hold 10", "hold 15", "hold 20", "hold 25", "hold 30", "hold 35", "hold 40", "hold 60", "tp 2% cap 30", "tp 4% cap 30", "tp 6% cap 30",
        "tp 2% cap 20", "tp 4% cap 20", "tp 1% cap 30", "tp 2% cap 25", "tp 6% cap 45", "tp 6% cap 50", "tp 8% cap 60"]
SCN = [("analyst", "ANALYST: end of T+2, no minOut, lag 2"), ("2|top|2", "REAL: top of T+2, minOut 3%, lag 2"), ("2|top|1", "lag 1"), ("2|top|3", "lag 3"),
       ("3|top|2", "buy at T+3, lag 2"), ("3|top|3", "buy at T+3, lag 3"), ("2|end|2", "end of T+2 with minOut, lag 2")]
out = {}
for gname, pr in GROUPS:
    g = [r for r in R if pr(r)]
    print(f"\n==== {gname}: {len(g)} pools ====")
    for stake in ("0.002", "0.0058"):
        print(f"  -- stake {stake} ETH (${USD[stake]:.0f}); per exit: fills/attempts, pulled, mean gross of the fills | EV $ per attempt [95% CI]")
        for sc, scn in SCN:
            if stake == "0.0058" and sc not in ("analyst", "2|top|2", "3|top|3"): continue
            print(f"    {scn}")
            for e in SHOW:
                L = line(g, sc, e, stake); out[(gname, stake, sc, e)] = L
                mf = "   -   " if L["mean_fill"] is None else f"{L['mean_fill']:+7.2%}"
                print(f"      {e:14s} {L['fills']:3d}/{L['n']:<3d} pulled {L['pulled']:2d}  gross {mf} | EV ${L['ev']:+.4f} [{L['ci'][0]:+.3f}, {L['ci'][1]:+.3f}]")
        # the execution mixture
        print(f"    MIXTURE (buy T+2 75% / T+3 25%; sell lag 1/2/3 at 25/50/25%; top of block): EV $ per attempt [95% CI]")
        for e in SHOW:
            v = [mix(r, stake, e) for r in g]; lo, hi = boot(v)
            out[(gname, stake, "mix", e)] = {"ev": sum(v) / len(v), "ci": (lo, hi)}
            print(f"      {e:14s} EV ${sum(v) / len(v):+.4f} [{lo:+.3f}, {hi:+.3f}]")

# ---- per 6-h slice, real execution, regime and no holder
SL = [calendar.timegm((2026, 10, 11, 1, 0, 0)) + 6 * 3600 * k for k in range(7)] + [10 ** 11]
NM = ["Oct 11 01-07", "Oct 11 07-13", "Oct 11 13-19", "Oct 11 19-01", "Oct 12 01-07", "Oct 12 07-13", "Oct 12 13-14:14"]
print("\n==== per 6-h slice, REAL (top of T+2, minOut, lag 2), 0.002: fills/attempts, mean gross of fills at hold 10 / 20 / 30 / 60 (pulled), EV $ per attempt at hold 30 ====")
for k, nm in enumerate(NM):
    for gname, pr in (("regime", REG), ("no holder", NONE)):
        g = [r for r in R if pr(r) and SL[k] <= r["ts"] < SL[k + 1]]
        if not g: continue
        cells = []
        for e in ("hold 10", "hold 20", "hold 30", "hold 60"):
            L = line(g, "2|top|2", e)
            cells.append(("  -  " if L["mean_fill"] is None else f"{L['mean_fill']:+6.1%}") + f" ({L['pulled']})")
        L30 = line(g, "2|top|2", "hold 30")
        print(f"  {nm:16s} {gname:9s} fills {L30['fills']:3d}/{L30['n']:<3d} " + " / ".join(cells) + f" | EV hold 30 ${L30['ev']:+.3f}")

# ---- who reverts: the router's buys in [T, T+1] vs fills
print("\n==== fills vs the router's buys in [T, T+1] (REAL, 0.002) ====")
for gname, pr in (("regime", REG), ("no holder", NONE)):
    c = collections.Counter((min(r["router_buys_T1"], 3), r["sc"]["0.002|2|top|2"]["fill"]) for r in R if pr(r))
    print(f"  {gname}: " + ", ".join(f"router buys {k[0]}{'+' if k[0] == 3 else ''}: {'fill' if k[1] else 'revert'} {v}" for k, v in sorted(c.items())))
json.dump({f"{a}|{b}|{c}|{d}": v for (a, b, c, d), v in out.items()}, open(K("k03_tables.json"), "w"))
