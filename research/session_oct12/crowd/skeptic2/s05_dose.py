"""skeptic2 tests on own data (s04_pools.json):
(A) re-find the early outsider pools (a non-crowd, non-launch-wallet sender buying >= 0.0005 ETH at + 1..+ 10; the + 1 bot apart);
(B) dose-response: in the cap branch (alive at + 78, no trigger by + 60: our sell is the cap's, landing + 80), the pull by + 80..+ 150 against
    the outside ETH still held at + 78 (non-bot), and against the biggest single holder;
(C) the pull hazard per pool-block before the crowd, by age band and by the outside ETH held at that block (a time-varying dose);
(D) the crowd's trigger by + 60 (where the rule's gain comes from) and the wave against an early holder's size;
(E) the + 1 bot as a natural experiment, our own way; (F) by launch day."""
from common import *
import collections, math
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"; MIN = 5 * 10 ** 14; REAL = 5 * 10 ** 15
P = json.load(open(J("s04_pools.json")))
def day(p): return time.strftime("%m-%d", time.gmtime(p["ts"]))
def wallets(p, upto):
    """outside wallets (class other, by tx sender) -> {w: dict(eth_in, tok_in, tok_out, first_off, first_eth, bot)} from swaps with off <= upto"""
    W = {}
    for s in p["sw"]:
        if s["off"] > upto: break
        if s["k"] != "other" or not s["from"]: continue
        w = W.setdefault(s["from"], {"eth_in": 0, "tok_in": 0, "tok_out": 0, "first_off": None, "first_eth": 0, "bot": s["from"] == BOT1, "buys": 0})
        if s["dq"] > 0:
            w["eth_in"] += s["dq"]; w["tok_in"] += -s["dt"]; w["buys"] += 1
            if w["first_off"] is None and s["dq"] >= MIN: w["first_off"] = s["off"]; w["first_eth"] = s["dq"]
        else: w["tok_out"] += s["dt"]
    return W
def held_eth(p, at, bot=False, min_first=MIN):
    """outside ETH still held at block offset `at` (paid ETH x unsold share), non-bot unless bot=True; and the biggest single holding"""
    tot = 0; big = 0; n = 0
    for w, v in wallets(p, at).items():
        if v["bot"] != bot and not (bot is None): continue
        if v["first_off"] is None or v["eth_in"] < min_first: continue
        frac = 1 - min(1, v["tok_out"] / v["tok_in"]) if v["tok_in"] else 0
        if frac < 0.5: continue
        h = v["eth_in"] * frac; tot += h; big = max(big, h); n += 1
    return tot / 1e18, big / 1e18, n
def pulled_by(p, x): return p["pull"] is not None and p["pull"]["off"] <= x
def crowd_by(p, x): return p["frb"] is not None and p["frb"] <= x
# ---------- (A)
early = []; analog = []
for p in P:
    W = wallets(p, 10)
    nb = [(w, v) for w, v in W.items() if not v["bot"] and v["first_off"] is not None and 1 <= v["first_off"] <= 10]
    if nb: early.append(p)
    if any(1 <= v["first_off"] <= 5 and v["first_eth"] >= 15 * 10 ** 14 for w, v in nb): analog.append(p)
print(f"(A) pools {len(P)}; with a non-bot outside buy >= 0.0005 ETH at +1..+10: {len(early)}; analogs (>= 0.0015 ETH at +1..+5): {len(analog)}")
print("    analog pools:", [(utc(p["ts"]), p["pool"][:10]) for p in analog])
# ---------- (B)
cap = [p for p in P if not pulled_by(p, 79) and (p["trig"] is None or p["trig"] > 60) and p["win"] >= 150]
print(f"\n(B) cap branch: alive at +79, no trigger by +60 (our sell lands +80): {len(cap)} pools")
XS = (80, 83, 85, 88, 90, 95, 100, 120, 150)
def row(name, g):
    n = len(g); s = f"  {name:<44} n {n:>4}:"
    for x in XS:
        k = sum(1 for p in g if pulled_by(p, x)); s += f" +{x} {k:>3}"
    k90 = sum(1 for p in g if pulled_by(p, 90)); k100 = sum(1 for p in g if pulled_by(p, 100))
    lo, hi = wilson(k90, n)
    s += f" | by +90 {100*k90/max(n,1):.1f}% (Wilson {100*lo:.1f}-{100*hi:.1f}%, exact upper {100*cp_upper(k90, n):.1f}%)"
    print(s); return n, k90, k100
for at in (78,):
    bins = [(0, 0), (1e-9, 0.001), (0.001, 0.002), (0.002, 0.004), (0.004, 1e9)]
    print(f"  by the total non-bot outside ETH still held at +{at} (pulled by +X, any crowd):")
    G = collections.defaultdict(list)
    for p in cap:
        t, b, n = held_eth(p, at)
        for lo, hi in bins:
            if (t == 0 and lo == 0 and hi == 0) or (lo > 0 and lo <= t < hi): G[(lo, hi)].append(p)
    for k in bins: row(f"held {k[0]:.4f}-{k[1]:.4f} ETH", G[k])
    print(f"  by the biggest single non-bot holding at +{at}:")
    G = collections.defaultdict(list)
    for p in cap:
        t, b, n = held_eth(p, at)
        for lo, hi in bins:
            if (b == 0 and lo == 0 and hi == 0) or (lo > 0 and lo <= b < hi): G[(lo, hi)].append(p)
    for k in bins: row(f"biggest {k[0]:.4f}-{k[1]:.4f} ETH", G[k])
    # a trend test: logistic-free, Cochran-Armitage over the 5 bins for pulled by +90 / +100 / +120
    def ca(x):
        rows = []
        for i, k in enumerate(bins):
            g = [p for p in cap if (lambda t: (t == 0 and k[1] == 0) or (k[0] > 0 and k[0] <= t < k[1]))(held_eth(p, at)[0])]
            rows.append((i, len(g), sum(1 for p in g if pulled_by(p, x))))
        N = sum(r[1] for r in rows); R = sum(r[2] for r in rows); pbar = R / N
        sx = sum(r[0] * r[1] for r in rows) / N
        num = sum(r[0] * (r[2] - r[1] * pbar) for r in rows)
        den = math.sqrt(pbar * (1 - pbar) * sum(r[1] * (r[0] - sx) ** 2 for r in rows))
        z = num / den if den else 0; return z, 0.5 * math.erfc(z / math.sqrt(2))
    for x in (90, 100, 120, 150):
        z, pz = ca(x); print(f"  Cochran-Armitage trend (total held bins) pulled by +{x}: z {z:.2f}, one-sided p {pz:.2g}")
# ---------- (C) hazard per pool-block before the crowd's first real buy
print("\n(C) pull hazard per pool-block, before the crowd's first real buy, by the non-bot outside ETH held at the block before (positions to +80 known; later: as at +80)")
H = collections.defaultdict(lambda: [0, 0])
bands = [(3, 40), (41, 78), (79, 90), (91, 110), (111, 150)]
dose_bins = [(0, 0), (1e-9, 0.001), (0.001, 0.002), (0.002, 1e9)]
for p in P:
    lim = min(150, p["win"])
    # held ETH per offset (piecewise: recompute at each swap offset <= 80)
    offs = sorted({s["off"] for s in p["sw"] if s["off"] <= 80 and s["k"] == "other"})
    cache = {}
    def held_at(b):
        a = min(b - 1, 80); key = max([o for o in offs if o <= a], default=-1)
        if key not in cache: cache[key] = held_eth(p, key)[0] if key >= 0 else 0.0
        return cache[key]
    for b in range(3, lim + 1):
        if p["pull"] is not None and p["pull"]["off"] < b: break
        if p["frb"] is not None and p["frb"] < b: break
        band = next((bd for bd in bands if bd[0] <= b <= bd[1]), None)
        h = held_at(b); db = next(d for d in dose_bins if (h == 0 and d[1] == 0) or (d[0] > 0 and d[0] <= h < d[1]))
        ev = p["pull"] is not None and p["pull"]["off"] == b and (p["frb"] is None or p["frb"] > b)
        H[(band, db)][0] += 1; H[(band, db)][1] += ev
for band in bands:
    s = f"  age +{band[0]}..+{band[1]}:"
    for db in dose_bins:
        n, k = H[(band, db)]; s += f"  held {db[0]:.3f}-{min(db[1],9):.3f}: {k}/{n} ({1e3*k/max(n,1):.2f}/1000 blocks)"
    print(s)
# ---------- (D) the crowd's trigger by + 60 and the wave vs the early holder
print("\n(D) the rule's gain window: trigger by +60 (sell at trigger + 20) and the crowd's ETH in [trigger, trigger + 20], by the biggest non-bot holding at +10")
def wave(p):
    if p["trig"] is None: return 0.0
    return sum(s["dq"] for s in p["sw"] if s["k"] in ("crowd", "crowd2", "crowd_s") and s["dq"] > 0 and p["trig"] <= s["off"] <= p["trig"] + 20) / 1e18
G = collections.defaultdict(list)
for p in P:
    if p["win"] < 150: continue
    b = held_eth(p, 10)[1]
    k = "none" if b == 0 else "<0.001" if b < 0.001 else "0.001-0.002" if b < 0.002 else ">=0.002"
    G[k].append(p)
for k in ("none", "<0.001", "0.001-0.002", ">=0.002"):
    g = G[k]; n = len(g)
    if not n: continue
    t60 = sum(1 for p in g if p["trig"] is not None and p["trig"] <= 60); w = [wave(p) for p in g if p["trig"] is not None and p["trig"] <= 60]
    print(f"  {k:<12} n {n:>4}: trigger by +60 {t60} ({100*t60/n:.1f}%, Wilson {100*wilson(t60,n)[0]:.1f}-{100*wilson(t60,n)[1]:.1f}%); wave ETH median {pct(w,.5) or 0:.3f} mean {sum(w)/max(len(w),1):.3f};"
          f" crowd by +78 {100*sum(1 for p in g if crowd_by(p,78))/n:.1f}%; pulled before any crowd by +150 {100*sum(1 for p in g if pulled_by(p,150) and not crowd_by(p,p['pull']['off']))/n:.1f}%")
# ---------- (E) the + 1 bot
print("\n(E) the + 1 bot (0x776e5a2a) at + 1..+ 3 vs not, no other early (+1..+10) non-bot holder; cap branch pulled by +X")
def botin(p): return any(s["bot"] and s["dq"] > 0 and s["off"] <= 3 for s in p["sw"])
def nb10(p): return held_eth(p, 10)[1] > 0
row("bot, no other early holder", [p for p in cap if botin(p) and not nb10(p)])
row("no bot, no other early holder", [p for p in cap if not botin(p) and not nb10(p)])
row("no bot, nobody at all by +78", [p for p in cap if not botin(p) and held_eth(p, 78, bot=None)[2] == 0])
# ---------- (F) by day: cap branch, pulled by +85/+90/+100 with a non-bot holder at +78 vs none, and the earliest pull
print("\n(F) by launch day, cap branch: [holder at +78] pulled by +85/+90/+100/+120 of n | [no holder] ... | earliest pull with a holder")
for d in sorted({day(p) for p in cap}):
    g = [p for p in cap if day(p) == d]; h = [p for p in g if held_eth(p, 78)[0] > 0]; z = [p for p in g if held_eth(p, 78)[0] == 0]
    f = lambda gg: "/".join(str(sum(1 for p in gg if pulled_by(p, x))) for x in (85, 90, 100, 120)) + f" of {len(gg)}"
    e = min([p["pull"]["off"] for p in h if p["pull"]], default=None)
    print(f"  {d}: holder {f(h):<22} none {f(z):<22} earliest pull (holder pools) {e}")
