"""Skeptic 1: returns, dollars and sample size of every exit in the reaction regime (offline; k01 pools, k02 replay, k04 regime).
Sets: OURS (our 5 real fills, our real entry); REG (ours + an outsider holding at T+2..T+10, engine trigger: n 11); REG-cf1d (without
0xcf1d880b: the pool whose holder bought 140 blocks before T); AN10 (the analyst's 'held from T+2' set: REG with 0x8985e55f in (its
router never bought >= 0.005, the engine would not fire) and 0xe12fa945 / 0x049464f8 out (the outsider sold by T+62)).
EV = $ x mean gross - $0.02 (gas, as the analyst); $5 at 0.002 ETH, $13 at 0.0058 ETH. CI: 95% pool bootstrap (10,000).
Break-even pull rate q* = (w - g) / (1 + w): w the survivors' mean, g = 0.02 / $."""
import json, random, statistics as st
from k02_sim import *
D = load(); P = {p["pid"]: p for p in D["pools"]}
R = json.load(open(os.path.join(H, "k04_regime.json")))
reg = [r["pid"] for r in R]; ours = [r["pid"] for r in R if r["ours"]]
an = [p for p in reg if not p.startswith(("0xe12fa945", "0x049464f8"))] + [k for k in P if k.startswith("0x8985e55f")]
SETS = [("OURS", ours), ("REG", reg), ("REG-cf1d", [p for p in reg if not p.startswith("0xcf1d880b")]), ("AN10", an)]
EX = [("hold", N) for N in (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60)] + [("tp", (tp, c)) for tp in (0.02, 0.03, 0.04, 0.06, 0.08) for c in (30, 40, 45, 50)]
def T_of(p): return p["Teng"] if p["Teng"] is not None else p["T"]
cache = {}
def ret(pid, stake, ex):
    k = (pid, stake)
    if k not in cache: cache[k] = Sim(P[pid], T_of(P[pid]), stake)
    s = cache[k]
    return s.hold(ex[1]) if ex[0] == "hold" else s.tp(ex[1][0], ex[1][1])[0]
def boot(v, B=10000, seed=11):
    rnd = random.Random(seed); n = len(v)
    m = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B)); return m[int(.025 * B)], m[int(.975 * B)]
def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5) / d; return max(0, c - h), min(1, c + h)
name = lambda ex: f"hold {ex[1]}" if ex[0] == "hold" else f"tp {int(ex[1][0] * 100)}% cap {ex[1][1]}"
out = {}
for sn, ids in SETS:
    print(f"\n== {sn}: n {len(ids)}  ({', '.join(i[:10] for i in ids)})")
    print(f"  {'exit':15s} {'mean':>8s} {'median':>8s} {'pulled':>7s} {'Wilson95':>12s} {'surv':>7s} {'q* $5':>6s} | {'EV $5':>7s} {'CI':>18s} | {'EV $13':>7s} {'CI':>18s} | per pool")
    for ex in EX:
        v = [ret(i, 2 * 10 ** 15, ex) for i in ids]; v13 = [ret(i, 58 * 10 ** 14, ex) for i in ids]
        k = sum(1 for x in v if x <= -1); sv = [x for x in v if x > -1]; w = st.mean(sv) if sv else 0
        lo, hi = boot(v); lo13, hi13 = boot(v13); wl, wh = wil(k, len(v)); q5 = (w - 0.02 / 5) / (1 + w)
        m = st.mean(v); m13 = st.mean(v13)
        out[(sn, name(ex))] = {"mean": m, "pulled": k, "n": len(v)}
        print(f"  {name(ex):15s} {m:+8.2%} {st.median(v):+8.2%} {k:3d}/{len(v):<3d} {wl:5.1%}-{wh:5.1%} {w:+7.2%} {q5:6.1%} | {5 * m - .02:+7.3f} [{5 * lo - .02:+.3f},{5 * hi - .02:+.3f}] |"
              f" {13 * m13 - .02:+7.3f} [{13 * lo13 - .02:+.3f},{13 * hi13 - .02:+.3f}] | " + " ".join("-100" if x <= -1 else f"{100 * x:+.1f}" for x in v))
json.dump({f"{a}|{b}": c for (a, b), c in out.items()}, open(os.path.join(H, "k07_stats.json"), "w"), indent=0)
