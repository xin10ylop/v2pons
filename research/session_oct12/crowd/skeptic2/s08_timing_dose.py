"""does more outside ETH bring the abort pull EARLIER (not only more often)? Cap-branch pools (alive at + 79, no trigger by + 60) pulled before any crowd
by + 300: the pull offset against the outside ETH held at + 78 (non-bot, and with the + 1 bot), Spearman rho and bins; and pools pulled by + 100 against
those pulled + 101..+ 300 in held ETH. Also the trigger branch since Oct 10: pull minus trigger for triggers <= + 60."""
from common import *
import collections, math
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"; MIN = 5 * 10 ** 14
P = json.load(open(J("s04_pools.json")))
def held(p, at, incl_bot=False):
    W = {}
    for s in p["sw"]:
        if s["off"] > at: break
        if s["k"] != "other" or not s["from"] or (s["from"] == BOT1 and not incl_bot): continue
        w = W.setdefault(s["from"], [0, 0, 0, 0])
        if s["dq"] > 0: w[0] += s["dq"]; w[1] += -s["dt"]; w[3] = max(w[3], s["dq"])
        else: w[2] += s["dt"]
    t = 0
    for w in W.values():
        if w[3] < MIN or not w[1]: continue
        f = 1 - min(1, w[2] / w[1])
        if f >= 0.5: t += w[0] * f
    return t / 1e18
def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v); i = 0
    while i < len(s):
        j = i
        while j < len(s) and v[s[j]] == v[s[i]]: j += 1
        for k in range(i, j): r[s[k]] = (i + j - 1) / 2
        i = j
    return r
def spearman(x, y):
    rx, ry = rank(x), rank(y); n = len(x); mx = sum(rx) / n; my = sum(ry) / n
    c = sum((a - mx) * (b - my) for a, b in zip(rx, ry)); d = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    rho = c / d if d else 0; z = rho * math.sqrt(n - 1); return rho, math.erfc(abs(z) / math.sqrt(2))
cap = [p for p in P if not (p["pull"] and p["pull"]["off"] <= 79) and (p["trig"] is None or p["trig"] > 60)]
ab = [p for p in cap if p["pull"] and (p["frb"] is None or p["frb"] > p["pull"]["off"])]
for incl in (False, True):
    x = [held(p, 78, incl) for p in ab]; y = [p["pull"]["off"] for p in ab]
    rho, pv = spearman(x, y)
    print(f"abort pulls (cap branch, pulled before any crowd, by +300): n {len(ab)}; held ETH at +78 {'with' if incl else 'without'} the +1 bot vs pull offset: Spearman rho {rho:+.3f} (two-sided p {pv:.2g})")
    for lo, hi in ((0, 1e-9), (1e-9, 0.001), (0.001, 0.002), (0.002, 0.004), (0.004, 9)):
        g = [yy for xx, yy in zip(x, y) if lo <= xx < hi]
        if g: print(f"    held {lo:.3f}-{hi:.3f}: n {len(g):>3} pull offset p10/25/50 {pct(g,.1)}/{pct(g,.25)}/{pct(g,.5)}; min {min(g)}")
# trigger branch since Oct 10
OCT10 = 1791590400
g = [p for p in P if p["trig"] is not None and p["trig"] <= 60]
for lab, gg in (("all", g), ("since Oct 10", [p for p in g if p["ts"] >= OCT10])):
    d = sorted(p["pull"]["off"] - p["trig"] for p in gg if p["pull"])
    print(f"trigger <= +60 ({lab}): n {len(gg)}; pulled by +300 {len(d)}; pull - trigger smallest {d[:8]}")
