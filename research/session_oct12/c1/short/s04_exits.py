"""The short exits (offline, s02_pools.json, sim.py, groups.py). For every usable triggered C-1 pool and both stakes (0.002 and 0.0058 ETH):
  T-aligned (the rule): our buy at the end of block T+2 (after every swap of T..T+2: the last price at or before T+2), in our 5 real
      pools at its real place (our real buy and sell taken out and re-simulated);
  holder-aligned (the reaction's clock): our buy right after the holder's first non-dust held buy when that came after T+2 (else as above),
      for the holder pools and for 0xbd9dc5f6's buys from 13:15 UTC (also those after T+62);
the gross return of every exit: hold N (sell sent at buy + N, lands + 2) for N in 5..60, and take-profit tp with cap 20..60 on the engine's
own price copy; -100% when pulled in or before the landing block. Writes s04_exits.json and prints the tables."""
from groups import *
import random, collections
HOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60]; TPS = [0.02, 0.03, 0.04, 0.06, 0.08]; CAPS = [20, 30, 40, 45, 50, 60]
STAKES = {"0.002": 2 * 10 ** 15, "0.0058": 58 * 10 ** 14}
EXITS = [f"hold {n}" for n in HOLDS] + [f"tp {int(tp * 100)}% cap {c}" for c in CAPS for tp in TPS]
D = load(); P = D["pools"]

def run(t, cs0):
    r = {}
    for n in HOLDS: r[f"hold {n}"] = t.hold(n)[0]
    tpx = {}
    for c in CAPS:
        for tp in TPS:
            g, why, at = t.take_profit(tp, c, cs0); k = f"tp {int(tp * 100)}% cap {c}"; r[k] = g; tpx[k] = (why, at)
    return r, tpx

def trade_at(p, kind, stake, h=None):
    """kind 'T': entry at T+2 (ours: our real place); kind 'H': right after swap h (the holder's buy)"""
    ours_b = [s for s in p["sw"] if s["cls"] == "ours" and s["buy"]]
    if ours_b:
        b = ours_b[0]; skip = {s["tx"] for s in p["sw"] if s["cls"] == "ours"}; i = p["sw"].index(b); prev = p["sw"][i - 1]
        t = Trade(p, i - 1, prev["sqrtP"], prev["liq"], b["bn"], stake, skip=skip, fee0=prev["fee"])
        return t, copy_before(p, (prev["bn"], prev["li"])), b["off"] - p["T"]
    if kind == "H" and h is not None and h["off"] > p["T"] + 2:
        i = p["sw"].index(h)
        if p["pullpos"] and (h["bn"], h["li"]) > tuple(p["pullpos"]): return None
        t = Trade(p, i, h["sqrtP"], h["liq"], h["bn"], stake, fee0=h["fee"]); return t, copy_before(p, (h["bn"], h["li"])), h["off"] - p["T"]
    Eb = p["lb"] + p["T"] + 2; i, sp, L, fee = entry_state(p, Eb); s = p["sw"][i]
    t = Trade(p, i, sp, L, Eb, stake, fee0=fee); return t, copy_before(p, (s["bn"], s["li"])), 2

rows = []; skipped = collections.Counter()
for p in sorted(P, key=lambda p: p["ts"]):
    u = usable(p, D)
    if u: skipped[u] += 1; continue
    g, h, sub = classify(p); b13 = bd13(p)
    if g == "sold": skipped["an outsider >= 0.001 sold again by T+62 (left out)"] += 1; continue
    bdh = None
    if b13:   # the reaction clock for 0xbd9dc5f6 from 13:15: its first >= 0.001 ETH buy
        bdh = next(s for s in p["sw"] if s["buy"] and s.get("from") == BD and s["eth"] >= 0.001)
    row = {"pid": p["pid"], "ts": p["ts"], "slice": slice_of(p["ts"]), "group": g, "sub": sub, "bd13": b13, "T": p["T"],
           "pull_T": None if p["pull"] is None else p["pull"] - p["T"], "res": {}}
    for kind in ("T", "H"):
        hh = h if g == "holder" else (bdh if b13 else None)
        if kind == "H" and g not in ("ours", "holder") and not b13: continue
        for sk, st in STAKES.items():
            x = trade_at(p, kind, st, hh)
            if x is None: continue
            t, cs0, eoff = x; r, tpx = run(t, cs0)
            row["res"][f"{kind} {sk}"] = r; row[f"entry_{kind}"] = eoff; row[f"tpx_{kind} {sk}"] = tpx
            row[f"pull_after_entry_{kind}"] = None if t.pullb is None else t.pullb - t.Eb
            row[f"tokens_{kind} {sk}"] = t.tokens
    rows.append(row)
json.dump({"rows": rows, "exits": EXITS, "stakes": list(STAKES), "skipped": skipped, "head": D["head"]}, open(S("s04_exits.json"), "w"))

# ------------------------------------------------------------------ tables
def stats(v):
    v = sorted(v); n = len(v)
    if not n: return None
    surv = [x for x in v if x > -1]
    return {"n": n, "mean": sum(v) / n, "median": v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2, "up": sum(1 for x in v if x > 0),
            "pulled": sum(1 for x in v if x <= -1), "surv_mean": sum(surv) / len(surv) if surv else None}
def boot(v, B=10000, seed=7):
    rnd = random.Random(seed); n = len(v); ms = sorted(sum(v[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return ms[int(0.025 * B)], ms[int(0.975 * B)]
def sel(kind, pred):
    return [r for r in rows if f"{kind} 0.002" in r["res"] and pred(r)]
GROUPS_T = [("ours (our 5 fills)", lambda r: r["group"] == "ours"),
            ("holder early (h <= T+5)", lambda r: r["group"] == "holder" and r["sub"] == "early"),
            ("holder later (h > T+5)", lambda r: r["group"] == "holder" and r["sub"] == "later"),
            ("bd9dc5f6 from 13:15 (any offset)", lambda r: r["bd13"]),
            ("REGIME: ours + holders + bd13", lambda r: r["group"] in ("ours", "holder") or r["bd13"]),
            ("  of which held from <= T+5 (ours + early)", lambda r: r["group"] == "ours" or (r["group"] == "holder" and r["sub"] == "early")),
            ("no holder (none, not bd13)", lambda r: r["group"] == "none" and not r["bd13"])]
def table(kind, groups, stake="0.002"):
    out = []
    for name, pr in groups:
        g = sel(kind, pr)
        if not g: continue
        out.append(f"\n  {name}: n {len(g)}")
        out.append(f"    {'exit':18s} {'n':>3s} {'mean':>8s} {'median':>8s} {'up':>4s} {'pulled':>6s} {'surv.mean':>9s}  95% CI of the mean (bootstrap)")
        for e in EXITS:
            v = [r["res"][f"{kind} {stake}"][e] for r in g]; s = stats(v); lo, hi = boot(v)
            out.append(f"    {e:18s} {s['n']:3d} {s['mean']:+8.2%} {s['median']:+8.2%} {s['up']:4d} {s['pulled']:6d} {'' if s['surv_mean'] is None else format(s['surv_mean'], '+9.2%'):>9s}  [{lo:+.1%}, {hi:+.1%}]")
    return "\n".join(out)
print(f"usable pools {len(rows)}; left out: {dict(skipped)}")
print(f"group sizes (T-aligned): {collections.Counter((r['group'], r['sub'], r['bd13']) for r in rows)}")
print("\n== A. T-aligned (the rule: our buy at the end of block T+2), stake 0.002 ETH, gross returns ==")
print(table("T", GROUPS_T))
GROUPS_H = [("ours (our 5 fills)", lambda r: r["group"] == "ours"),
            ("holder early (entry T+2..T+5)", lambda r: r["group"] == "holder" and r["sub"] == "early"),
            ("holder later (entry at the holder's buy, T+15..56)", lambda r: r["group"] == "holder" and r["sub"] == "later"),
            ("bd9dc5f6 from 13:15 (entry at its buy, T+18..121)", lambda r: r["bd13"]),
            ("REGIME (holder-aligned): ours + holders + bd13", lambda r: r["group"] in ("ours", "holder") or r["bd13"])]
print("\n== B. holder-aligned (our buy right after the holder's own buy: the reaction's clock), stake 0.002 ETH ==")
print(table("H", GROUPS_H))
# stake sensitivity
d = [abs(r["res"]["T 0.002"][e] - r["res"]["T 0.0058"][e]) for r in rows for e in EXITS if r["res"]["T 0.002"][e] > -1]
print(f"\nstake 0.002 vs 0.0058 ETH, same pool and exit (survivors): max |difference| {max(d):.3%}, mean {sum(d) / len(d):.4%}")
# slices
print("\n== C. per 6-h slice (T-aligned, 0.002): mean / pulled-before-sell / n ==")
SL = ["hold 10", "hold 20", "hold 25", "hold 30", "hold 60", "tp 3% cap 30", "tp 4% cap 30"]
print(f"  {'slice':16s} {'group':8s} " + " ".join(f"{e:>17s}" for e in SL))
for sn in SLICE_NAMES:
    for gname, pr in (("regime", lambda r: r["group"] in ("ours", "holder") or r["bd13"]), ("none", lambda r: r["group"] == "none" and not r["bd13"])):
        g = sel("T", lambda r: r["slice"] == sn and pr(r))
        if not g: continue
        cells = []
        for e in SL:
            v = [r["res"]["T 0.002"][e] for r in g]; s = stats(v); cells.append(f"{s['mean']:+7.1%} {s['pulled']:2d}/{s['n']:<3d}")
        print(f"  {sn:16s} {gname:8s} " + " ".join(f"{c:>17s}" for c in cells))
print("\n== C2. per 6-h slice, holder-aligned regime (0.002) ==")
for sn in SLICE_NAMES:
    g = sel("H", lambda r: r["slice"] == sn and (r["group"] in ("ours", "holder") or r["bd13"]))
    if not g: continue
    cells = []
    for e in SL:
        v = [r["res"]["H 0.002"][e] for r in g]; s = stats(v); cells.append(f"{s['mean']:+7.1%} {s['pulled']:2d}/{s['n']:<3d}")
    print(f"  {sn:16s} {'regime':8s} " + " ".join(f"{c:>17s}" for c in cells))
# per pool detail for the regime
print("\n== D. every regime pool (T-aligned and holder-aligned, 0.002): entry, pull after our buy, hold 10/20/30/60, tp 4% cap 30 ==")
for r in rows:
    if not (r["group"] in ("ours", "holder") or r["bd13"]): continue
    a = r["res"]["T 0.002"]; b = r["res"].get("H 0.002")
    f = lambda x: "  -100%" if x <= -1 else f"{x:+7.1%}"
    tpx = r["tpx_T 0.002"]["tp 4% cap 30"]
    print(f"  {utc(r['ts'])} {r['pid'][:10]} {r['group']:6s} {r['sub'] or '':5s} {'bd13' if r['bd13'] else '    '} pull T+{r['pull_T']}"
          f" | T: pull@buy+{r['pull_after_entry_T']} " + " ".join(f(a[e]) for e in ("hold 10", "hold 20", "hold 30", "hold 60", "tp 4% cap 30")) + f" (tp: {tpx[0]} sent buy+{tpx[1]})"
          + (f" | H: entry T+{r['entry_H']} pull@buy+{r['pull_after_entry_H']} " + " ".join(f(b[e]) for e in ("hold 10", "hold 20", "hold 30", "hold 60", "tp 4% cap 30")) if b else ""))
