"""Break-even and expected dollars per trade for the candidate exits (offline, s04_exits.json). $5 a trade = the 0.002 ETH returns, $13 = the
0.0058 ETH returns (a hold's return differs by < 0.07 pp between them); gas $0.02 a trade (the research convention; the engine's own round trip at
0.02 gwei is $0.013). EV = stake x mean gross - $0.02, its 95% CI by a pool bootstrap (10,000 resamples). Break-even pull rate (a pull = -100%):
(w - g) / (1 + w), w = the survivors' mean gross, g = gas / stake. Also the split by the trigger's offset from the launch (the family's trigger
max_blocks is config too) and the router's stop in our own 5 pools."""
from groups import *
import random
X = json.load(open(S("s04_exits.json"))); R = X["rows"]; GAS = 0.02
def boot(v, B=10000, seed=11):
    rnd = random.Random(seed); n = len(v); ms = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B)); return ms[int(.025 * B)], ms[int(.975 * B)]
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]
SETS = [("regime T-aligned", "T", REG), ("regime holder-aligned", "H", REG), ("ours (5 fills)", "T", lambda r: r["group"] == "ours"),
        ("held from <= T+5 (ours + early)", "T", lambda r: r["group"] == "ours" or r["sub"] == "early"), ("no holder (contrast)", "T", lambda r: r["group"] == "none" and not r["bd13"])]
CAND = ["hold 10", "hold 20", "hold 25", "hold 30", "hold 40", "hold 60", "tp 3% cap 30", "tp 6% cap 30", "tp 3% cap 45", "tp 6% cap 45", "tp 8% cap 45", "tp 6% cap 50", "tp 8% cap 50", "tp 8% cap 60"]
def line(name, kind, pr, e, sub=lambda r: True):
    out = []
    for stake, usd in (("0.002", 5), ("0.0058", 13)):
        g = [r for r in R if f"{kind} {stake}" in r["res"] and pr(r) and sub(r)]
        v = [r["res"][f"{kind} {stake}"][e] for r in g]; n = len(v)
        if not n: return None
        k = sum(1 for x in v if x <= -1); s = [x for x in v if x > -1]; w = sum(s) / len(s) if s else 0; m = sum(v) / n; lo, hi = boot(v)
        gg = GAS / usd; be = (w - gg) / (1 + w); wl, wh = wilson(k, n)
        out.append((n, m, k, wl, wh, w, be, usd * m - GAS, usd * lo - GAS, usd * hi - GAS))
    a, b = out
    return (f"    {e:14s} n {a[0]:3d} mean {a[1]:+6.2%} pulled {a[2]}/{a[0]} (Wilson {a[3]:.0%}-{a[4]:.0%}) surv {a[5]:+6.2%} | break-even pull rate $5 {a[6]:+6.1%} $13 {b[6]:+6.1%}"
            f" | EV $5 {a[7]:+.3f} [{a[8]:+.3f}, {a[9]:+.3f}]  $13 {b[7]:+.3f} [{b[8]:+.3f}, {b[9]:+.3f}]")
for name, kind, pr in SETS:
    print(f"\n== {name} ==")
    for e in CAND:
        l = line(name, kind, pr, e)
        if l: print(l)
print("\n== by the trigger's offset from the launch (regime T-aligned / no holder), mean gross 0.002 and pulled ==")
for lo_, hi_ in ((0, 60), (61, 100), (101, 150), (151, 400)):
    for name, pr in (("regime", REG), ("none", lambda r: r["group"] == "none" and not r["bd13"])):
        g = [r for r in R if pr(r) and lo_ <= r["T"] <= hi_ and "T 0.002" in r["res"]]
        if not g: continue
        cells = []
        for e in ("hold 10", "hold 20", "hold 30", "hold 40", "hold 60", "tp 6% cap 45"):
            v = [r["res"]["T 0.002"][e] for r in g]; cells.append(f"{e} {sum(v) / len(v):+6.1%} ({sum(1 for x in v if x <= -1)})")
        print(f"  T in [{lo_:3d},{hi_:3d}] {name:6s} n {len(g):3d}: " + "  ".join(cells))
print("\n== T <= 100 only (trigger max_blocks 100 instead of 400): every exit lands before launch + 147, the earliest pull of any triggered pool ==")
for name, kind, pr in SETS[:2] + SETS[4:]:
    print(f"  {name}")
    for e in ("hold 10", "hold 20", "hold 30", "hold 40", "tp 6% cap 40", "tp 8% cap 40"):
        l = line(name, kind, pr, e, lambda r: r["T"] <= 100)
        if l: print(l)
# our 5 pools: the router's buys after our buy and its stop
print("\n== our 5 pools: the router's buys after our buy (offset from our buy, ETH), its last buy before the pull, the pull ==")
D = load()
for p in sorted(D["pools"], key=lambda p: p["ts"]):
    ob = [s for s in p["sw"] if s["cls"] == "ours" and s["buy"]]
    if not ob: continue
    b = ob[0]; end = p["pullpos"] or (1 << 62, 0)
    rb = [(s["bn"] - b["bn"], round(s["eth"], 3)) for s in p["sw"] if s["buy"] and s["cls"] == "router" and (s["bn"], s["li"]) > (b["bn"], b["li"]) and (s["bn"], s["li"]) < tuple(end) and s["bn"] - b["bn"] <= 200]
    print(f"  {utc(p['ts'])} {p['pid'][:10]} T+{p['T']} router buys after ours (to +200): {rb[:8]}{' ...' if len(rb) > 8 else ''} | pull at our buy + {None if not p['pullpos'] else p['pullpos'][0] - b['bn']}")
