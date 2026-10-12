"""crowd skipping or shrinking against an early holder's size: the crowd's own first real buy (not anyone's ETH buy) by + 60 / + 78, and its first
20-block wave (crowd ETH in [frb, frb + 20]), by the biggest non-bot outside holding bought at + 1..+ 10 and still held at + 10; the + 1 bot apart.
Fisher one-sided for fewer early crowds than in pools with no early holder."""
from common import *
import collections
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"; MIN = 5 * 10 ** 14
P = [p for p in json.load(open(J("s04_pools.json"))) if p["win"] >= 300]
def big10(p, bot=False):
    W = {}
    for s in p["sw"]:
        if s["off"] > 10: break
        if s["k"] != "other" or not s["from"] or ((s["from"] == BOT1) != bot): continue
        w = W.setdefault(s["from"], [0, 0, 0])
        if s["dq"] > 0: w[0] += s["dq"]; w[1] += -s["dt"]
        else: w[2] += s["dt"]
    return max([w[0] / 1e18 for w in W.values() if w[0] >= MIN and w[1] and w[2] < 0.5 * w[1]], default=0)
def wave(p):
    if p["frb"] is None: return None
    return sum(s["dq"] for s in p["sw"] if s["k"] in ("crowd", "crowd2", "crowd_s") and s["dq"] > 0 and p["frb"] <= s["off"] <= p["frb"] + 20) / 1e18
G = collections.defaultdict(list)
for p in P:
    b = big10(p); bot = big10(p, True) > 0
    k = "none" if b == 0 else "<0.001" if b < 0.001 else "0.001-0.0015" if b < 0.0015 else ">=0.0015"
    G[(k, bot)].append(p)
base = [p for p in P if big10(p) == 0]
b60 = sum(1 for p in base if p["frb"] is not None and p["frb"] <= 60); b78 = sum(1 for p in base if p["frb"] is not None and p["frb"] <= 78)
for bot in (False, True):
    print(f"the + 1 bot {'present' if bot else 'absent'} at + 1..+ 10:")
    for k in ("none", "<0.001", "0.001-0.0015", ">=0.0015"):
        g = G[(k, bot)]; n = len(g)
        if not n: continue
        c60 = sum(1 for p in g if p["frb"] is not None and p["frb"] <= 60); c78 = sum(1 for p in g if p["frb"] is not None and p["frb"] <= 78)
        w = [wave(p) for p in g if p["frb"] is not None and p["frb"] <= 78]
        f60 = fisher1(b60 - 0, len(base) - b60, c60, n - c60) if k != "none" else None
        print(f"  biggest early non-bot holding {k:<12} n {n:>4}: crowd by +60 {c60:>3} ({100*c60/n:5.1f}%, Wilson {100*wilson(c60,n)[0]:.1f}-{100*wilson(c60,n)[1]:.1f}%), by +78 {c78:>3} ({100*c78/n:5.1f}%);"
              f" first wave (crowd by +78) median {pct(w,.5) or 0:.3f} ETH" + (f"; one-sided p (fewer than no-holder pools, by +60) {f60:.2g}" if f60 is not None else ""))
