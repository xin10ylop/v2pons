"""Skeptic 2: stress of the short exits under the engine's real execution (offline; k02_exec.simulate on s02_pools.json data).
(1) the trigger window (the family's trigger max_blocks, config): 100 / 150 / 400;
(2) a FASTER operator, applied to EVERY fill (we hold from T+2 in every pool we enter, so every pool is a holder pool for us): the router's
    buys after our buy + k are dropped (it stops) and the launch wallet pulls at our buy + k + d; k 15..30, d 9 (the fastest stop->pull after
    our own buy, 0xb47b706f) and 0; the observed (our 5 fills): stop at buy + 27/30/37/47 (one paused through), pull at 36/84/97/115;
(3) the break-even pull rate of the best exits and what 0 pulls in n fills can bound;
(4) the engine's non-bot streak halt (5 fills in a row under +2%): how often a run of 5 comes up (it is per-family config: nonbot_halt 0 = off).
Execution: buy lands T+2 (75%) or T+3 (25%), top of block, minOut 3%; the sell lands 1/2/3 blocks after it is sent (25/50/25%); real gas."""
from sk import *
import k02_exec as KX
import random, collections, copy as cp
G = json.load(open(K("k01_gas.json"))); GF, GP, GR = G["per_fill_wei"] / 1e18, G["per_pulled_wei"] / 1e18, G["per_revert_wei"] / 1e18
X = json.load(open(K("k02_exec.json"))); R = X["rows"]; byp = {p["pid"]: p for p in KX.P}
USD = {"0.002": 5.0, "0.0058": 13.0}; ETHUSD = {"0.002": 2500.0, "0.0058": 13.0 / 0.0058}
WB = ((2, .75), (3, .25)); WL = ((1, .25), (2, .5), (3, .25))
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]
EXACT = lambda r: r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")
NONE = lambda r: r["group"] == "none" and not r["bd13"]
ALL = lambda r: True
EX = ["hold 10", "hold 20", "hold 25", "hold 30", "hold 35", "hold 40", "hold 60", "tp 2% cap 30", "tp 4% cap 30", "tp 6% cap 30", "tp 4% cap 25", "tp 6% cap 45", "tp 6% cap 50"]

def usd(x, e, stake):
    if not x["fill"]: return -GR * ETHUSD[stake]
    g, pulled, _ = x["res"][e]
    return USD[stake] * g - (GP if pulled else GF) * ETHUSD[stake]
def boot(v, B=4000, seed=3):
    rnd = random.Random(seed); n = len(v); ms = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B)); return ms[int(.025 * B)], ms[int(.975 * B)]
def trig_off(p):
    c = 0
    for s in p["sw"]:
        if s["cls"] != "ours" and s["buy"] and s.get("to") == ROUTER and (KX.seen_amount(s) or 0) >= KX.MIN_TRIG: return s["off"]
    return None

def sims(r, stake, reaction=None):
    """the mixture's scenarios for row r: [(weight, sim)]; reaction (k, d): the router stops after our buy + k, the pull at our buy + k + d"""
    p = byp[r["pid"]]; out = []
    for dB, a in WB:
        for lag, b in WL:
            if reaction is None:
                out.append((a * b, r["sc"][f"{stake}|{dB}|top|{lag}"])); continue
            k, d = reaction; t = trig_off(p)
            if t is None: out.append((a * b, {"fill": False})); continue
            B = p["lb"] + t + dB; q = cp.copy(p)
            q["sw"] = [s for s in p["sw"] if not (s["bn"] > B + k and s.get("to") == ROUTER and s["buy"])]
            pb = B + k + d
            if p["pullpos"] is None or pb < p["pullpos"][0]: q["pullpos"] = [pb, 0]
            out.append((a * b, KX.simulate(q, KX.STAKES[stake], dB, "top", lag)))
    return out
def ev(rows, e, stake, reaction=None, cache=None):
    v = []
    for r in rows:
        key = (r["pid"], stake, reaction)
        if cache is not None and key in cache: S = cache[key]
        else:
            S = sims(r, stake, reaction)
            if cache is not None: cache[key] = S
        v.append(sum(w * usd(x, e, stake) for w, x in S))
    return v

print("(1) trigger max_blocks (the engine's real trigger: the first router buy >= 0.005 ETH) x exit: EV $ per attempt at $5 [95% CI] (attempts)")
for nm, pr in (("holder regime", REG), ("held from T+2", EXACT), ("no holder", NONE)):
    print(f"  {nm}")
    for mb in (100, 150, 400):
        g = [r for r in R if pr(r) and (trig_off(byp[r["pid"]]) or 10 ** 9) <= mb]
        cells = []
        for e in ("hold 10", "hold 20", "hold 30", "tp 4% cap 30", "tp 6% cap 50", "hold 60"):
            v = ev(g, e, "0.002"); lo, hi = boot(v) if v else (0, 0)
            cells.append(f"{e}: {sum(v) / max(1, len(v)):+.3f} [{lo:+.2f},{hi:+.2f}]")
        print(f"    max_blocks {mb:3d} (n {len(g):3d})  " + "  ".join(cells))

print("\n(2) a faster operator applied to EVERY fill (the router stops after our buy + k, the pull at our buy + k + d): EV $ per attempt at $5 / $13, all usable pools (n 185)")
cache = {}
for k, d in ((47, 68), (30, 54), (27, 9), (25, 9), (22, 9), (20, 9), (15, 9), (27, 0), (20, 0)):
    cells = []
    for e in ("hold 10", "hold 15", "hold 20", "hold 25", "hold 30", "tp 2% cap 30", "tp 4% cap 30", "tp 6% cap 50"):
        v = ev(R, e, "0.002", (k, d), cache); v2 = ev(R, e, "0.0058", (k, d), cache)
        cells.append(f"{e}: {sum(v) / len(v):+.3f}/{sum(v2) / len(v2):+.3f}")
    print(f"  stop at buy+{k:2d}, pull at buy+{k + d:3d}: " + "  ".join(cells))

print("\n(3) break-even pull rate (w - g) / (1 + w) of the best exits (REAL mixture over the fills; w = the survivors' mean gross, g = gas / stake), and the pulls seen")
from math import comb
def cp_up(k, n, a=.05):
    lo, hi = k / n, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if sum(comb(n, i) * m ** i * (1 - m) ** (n - i) for i in range(k + 1)) > a: lo = m
        else: hi = m
    return hi
for nm, pr in (("holder regime", REG), ("held from T+2", EXACT), ("all usable", ALL)):
    g = [r for r in R if pr(r)]
    for e in ("hold 20", "hold 25", "hold 30", "tp 4% cap 30", "tp 6% cap 30", "tp 6% cap 50"):
        for stake in ("0.002", "0.0058"):
            fills = [(w, x["res"][e]) for r in g for w, x in sims(r, stake) if x["fill"]]
            W = sum(w for w, _ in fills); surv = [(w, y[0]) for w, y in fills if not y[1]]; pulled = sum(w for w, y in fills if y[1])
            wmean = sum(w * y for w, y in surv) / sum(w for w, _ in surv); gg = (GF * ETHUSD[stake]) / USD[stake]
            be = (wmean - gg) / (1 + wmean); nf = round(W); kp = round(pulled)
            under2 = sum(w for w, y in fills if y[0] < 0.02) / W
            if stake == "0.002":
                print(f"  {nm:14s} {e:13s} fills {nf:3d} (weighted), pulled {pulled:4.1f}; survivors' mean {wmean:+.2%}; break-even pull rate ${USD[stake]:.0f} {be:.2%}"
                      f"; one-sided 95% upper bound on the pull rate from {kp}/{nf}: {cp_up(kp, nf):.1%}; fills under +2%: {under2:.0%}", end="")
            else:
                print(f"; ${USD[stake]:.0f} {be:.2%}")

print("\n(4) the non-bot streak halt (FRONT_NONBOT_HALT 5: five fills in a row under +2% halt the family; reverted buys do not count), REAL dB 2 lag 2,"
      " fills in time order over all usable pools:")
for e in ("hold 10", "hold 20", "hold 30", "tp 4% cap 30", "tp 6% cap 50", "hold 60"):
    seq = [r["sc"]["0.002|2|top|2"]["res"][e][0] for r in sorted(R, key=lambda r: r["ts"]) if r["sc"]["0.002|2|top|2"]["fill"]]
    run = mx = trips = 0
    for x in seq:
        run = run + 1 if x < 0.02 else 0
        if run == 5: trips += 1; run = 0
    print(f"  {e:13s} fills {len(seq)}, under +2%: {sum(1 for x in seq if x < 0.02) / len(seq):.0%}; the halt would trip {trips} times (each needs the owner to clear it) unless the family sets nonbot_halt 0")
