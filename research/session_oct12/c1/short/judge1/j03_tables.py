"""Judge 1: per-attempt $ at $5 (0.002 ETH at $2,500) and pulls, engine-exact fills, for hold 20/25/30/35 and tp 4%/6% with caps 30/40
(plus hold 10/15/40/60 for reference), trigger max_blocks 400 (the box) and 100, in (a) the holder regime and (b) all triggered pools of the
line's launch shape; 95% pool-bootstrap CIs (10,000 resamples). Sensitivity: buy at T+3, sell lag 1 and 3. Writes j03_tables.json."""
from j02_sim import *
pools, head = load_pools()
line = [p for p in pools if p["shape"] == "line"]
stake = 2 * 10 ** 15
SHOW = ["hold 10", "hold 20", "hold 25", "hold 30", "hold 35", "hold 40", "hold 60", "tp 4% cap 30", "tp 6% cap 30", "tp 4% cap 40", "tp 6% cap 40"]
HOLDER = ("ours", "holder-pre", "holder-early", "holder-later", "bd13"); EXACT = ("ours", "holder-pre", "holder-early")
SETS = [("(a) holder regime", lambda r: r["reg"] in HOLDER), ("(a') held from T+2 (ours, holders in by T+5)", lambda r: r["reg"] in EXACT),
        ("(b) all triggered", lambda r: r["reg"] != "x"), ("    no holder", lambda r: r["reg"] in ("none", "sold"))]
OUT = {}
def table(rows, title, key):
    print(f"\n== {title}")
    for sname, f in SETS:
        R = [r for r in rows if f(r)]
        n = len(R); nf = sum(r["fill"] for r in R)
        print(f"  {sname}: attempts {n}, fills {nf}, reverts {n - nf} (" + ", ".join(f"{k} {v}" for k, v in collections.Counter(r['why'] for r in R if not r['fill']).items()) + ")")
        for ex in SHOW:
            v = [usd(r, ex, stake) for r in R]
            if not v: continue
            m = sum(v) / len(v); lo, hi = boot(v)
            F = [r for r in R if r["fill"]]
            pulled = sum(1 for r in F if r["res"][ex][1])
            gm = sum(r["res"][ex][0] for r in F) / len(F) if F else float("nan")
            surv = [r["res"][ex][0] for r in F if not r["res"][ex][1]]
            u2 = sum(1 for r in F if r["res"][ex][0] < 0.02)
            land = sorted(r["res"][ex][3] for r in F)
            print(f"    {ex:13s} pulled {pulled}/{nf}  gross of fills {gm:+.2%}  survivors {sum(surv) / max(1, len(surv)):+.2%}  $/attempt {m:+.3f} [{lo:+.3f}, {hi:+.3f}]  "
                  f"under +2%: {u2}/{nf}  landing buy+{land[0] if land else '-'}..{land[-1] if land else '-'}")
            OUT[f"{key}|{sname}|{ex}"] = {"n": n, "fills": nf, "pulled": pulled, "gross": gm, "usd": m, "ci": [lo, hi]}

for mb in (400, 100):
    rows = run(line, stake, mb)
    table(rows, f"max_blocks {mb}, buy at top of T+2, sell lag 2 (base)", f"{mb}|base")
    if mb == 400:
        print("\n  regime counts:", dict(collections.Counter(r["reg"] for r in rows)))
        print("  holder-regime pools:")
        for r in sorted([r for r in rows if r["reg"] in HOLDER], key=lambda r: r["ts"]):
            x = r["res"]["hold 30"] if r["fill"] else None
            print(f"    {utc(r['ts'])} {r['pid'][:10]} {r['reg']:12s} T +{r['T']:3d} {'FILL' if r['fill'] else 'rev '} pull@buy+{r['pull_after_buy']}"
                  + (f"  hold30 {x[0]:+.2%} hold60 {r['res']['hold 60'][0]:+.2%} tp4c40 {r['res']['tp 4% cap 40'][0]:+.2%}" if x else f"  (short {r.get('short', 0):+.2%})"))
for mb in (400, 100):
    for dB, lag, nm in ((3, 2, "buy at T+3"), (2, 1, "sell lag 1"), (2, 3, "sell lag 3")):
        rows = run(line, stake, mb, dB=dB, lag=lag)
        table(rows, f"max_blocks {mb}, {nm} (stress)", f"{mb}|{nm}")
json.dump(OUT, open(JD("j03_tables.json"), "w"), indent=0)
