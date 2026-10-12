"""Statistics of r06's replay: per stake x entry x sell landing; per day and per 6-h slice; the REPORT_W gate; $ a day after gas; the
crowd's first buy, the buyers before it, the pulls; the engine's dry pricing against the exact replay (all launches and the box's 24 h)."""
from common import *
import collections, statistics as stt, calendar
D = json.load(open(J("r06_rows.json"))); R = D["rows"]; EU = D["eth_usd"]; BF = D["base_fee"]
M = json.load(open(J("r01_meta.json")))
span_d = (M["head_ts"] - START_TS) / 86400
def summ(v):
    v = sorted(v); n = len(v)
    if not n: return None
    tot = sum(v); k = max(1, round(n * 0.1)); top = sum(v[-k:])
    return {"n": n, "mean": stt.mean(v), "median": stt.median(v), "p10": pct(v, .1), "p25": pct(v, .25), "p75": pct(v, .75), "p90": pct(v, .9), "worst": v[0], "best": v[-1],
            "win": sum(1 for x in v if x > 0), "top10_share": top / tot if tot else float("nan"), "mean_wo_top10": stt.mean(v[:-k]) if n > k else float("nan")}
def fmt(s):
    return (f"n {s['n']:>3}  mean {s['mean']*100:+6.2f}%  median {s['median']*100:+6.2f}%  p10 {s['p10']*100:+6.2f}  p25 {s['p25']*100:+6.2f}  p75 {s['p75']*100:+6.2f}  "
            f"p90 {s['p90']*100:+6.2f}  worst {s['worst']*100:+7.2f}%  best {s['best']*100:+7.2f}%  win {s['win']}/{s['n']}  top10% share {s['top10_share']*100:4.0f}%  mean w/o top10% {s['mean_wo_top10']*100:+.2f}%")
print(f"window: {utc(START_TS)} to {utc(M['head_ts'])} UTC ({span_d:.2f} days); launches of the line's shape {len(R) + len(D['skipped'])}, WETH token1 (skipped by the engine) {len(D['skipped'])}, replayed {len(R)}"
      f" = {len(R) / span_d:.1f} a day; base fee {BF / 1e9:.4f} gwei; ETH ${EU:,.0f} (USDG/WETH 0.01% pool); gas {D['gas']} -> ${(D['gas'][0] + D['gas'][1]) * BF / 1e18 * EU:.4f} a round trip")
print("\n== 1. the rule, every configuration (net = after gas; -100% if the first Burn lands at or before our sell's block)")
for q in D["stakes"]:
    for e in (1, 2, 3):
        for d in (1, 2):
            v = [r["r"][f"{q}|{e}|{d}"]["ret"] for r in R]
            print(f"q {q:.4f} (${q*EU:5.2f}) entry +{e} sell lands +{d}: {fmt(summ(v))}  pulled {sum(r['r'][f'{q}|{e}|{d}']['pulled'] for r in R)}")
    v = [r["r"][f"{q}|2|2|tail"]["ret"] for r in R]
    print(f"q {q:.4f}  entry +2 at the END of its block, lands +2: {fmt(summ(v))}")
print("\n== 2. gross (before gas) vs net vs the pool's own price move (no impact, no fees), entry +2, sell lands +2")
for q in (0.0012, 0.0036, 0.0058):
    g = [r["r"][f"{q}|2|2"]["gross"] for r in R]; n = [r["r"][f"{q}|2|2"]["ret"] for r in R]; m = [r["r"][f"{q}|2|2"]["move"] for r in R]
    print(f"q {q}: gross mean {stt.mean(g)*100:+.2f}% median {stt.median(g)*100:+.3f}% | net mean {stt.mean(n)*100:+.2f}% median {stt.median(n)*100:+.3f}% | price move mean {stt.mean(m)*100:+.2f}% median {stt.median(m)*100:+.3f}%")
def day_of(ts): return time.strftime("%m-%d", time.gmtime(ts))
def slice_of(ts): h = time.gmtime(ts).tm_hour // 6 * 6; return f"{day_of(ts)} {h:02d}-{h+6:02d}"
KEY = "0.0058|2|2"
print(f"\n== 3. per day and per 6-h slice ({KEY}: 0.0058 ETH, entry +2, sell lands +2; and 0.0012 / 0.0036)")
for lab, fn in (("day", day_of), ("6-h", slice_of)):
    g = collections.defaultdict(list)
    for r in R: g[fn(r["ts"])].append(r)
    for k in sorted(g):
        rs = g[k]; s = summ([r["r"][KEY]["ret"] for r in rs])
        hrs = 6.0 if lab == "6-h" else 24.0
        if lab == "day" and k == "10-10": hrs = 12.0
        if k == day_of(M["head_ts"]) and lab == "day": hrs = (M["head_ts"] - calendar.timegm(time.strptime("2026-" + k, "%Y-%m-%d"))) / 3600
        if lab == "6-h" and k.startswith(day_of(M["head_ts"])) and int(k[6:8]) <= time.gmtime(M["head_ts"]).tm_hour < int(k[6:8]) + 6: hrs = time.gmtime(M["head_ts"]).tm_hour - int(k[6:8]) + time.gmtime(M["head_ts"]).tm_min / 60
        m12 = stt.mean(r["r"]["0.0012|2|2"]["ret"] for r in rs); m36 = stt.mean(r["r"]["0.0036|2|2"]["ret"] for r in rs)
        print(f"  {lab} {k:<14} ({hrs:4.1f} h, {len(rs) / hrs * 24:5.0f}/day) {fmt(s)}  pulled {sum(r['r'][KEY]['pulled'] for r in rs)} | mean at 0.0012 {m12*100:+.2f}%, 0.0036 {m36*100:+.2f}%")
print("\n== 4. pulls (the pool's first Burn of liquidity > 0)")
bo = [r["burn_off"] for r in R if r["burn_off"] is not None]
print(f"pulled by the head: {len(bo)}/{len(R)}; offsets: <= +80 {sum(1 for b in bo if b <= 80)}, <= +100 {sum(1 for b in bo if b <= 100)}, <= +150 {sum(1 for b in bo if b <= 150)}, <= +300 {sum(1 for b in bo if b <= 300)}; "
      f"earliest {sorted(bo)[:12]}; median {stt.median(bo) if bo else None}")
print(f"who: {collections.Counter((r['burn_by_launcher'], (r['burn_to'] or '')[:10], r['burn_sel']) for r in R if r['burn_off'] is not None).most_common(6)}; fraction of the launch L removed: {collections.Counter(round(r['burn_frac'], 3) for r in R if r['burn_frac']).most_common(4)}")
for q in (0.0012, 0.0058):
    for e in (1, 2, 3):
        print(f"  pulled at or before our sell, q {q} entry +{e}: lands +1 {sum(r['r'][f'{q}|{e}|1']['pulled'] for r in R)}, lands +2 {sum(r['r'][f'{q}|{e}|2']['pulled'] for r in R)}")
print("\n== 5. the crowd's first real buy (crowd call shape, >= 0.005 WETH in) and the engine's first trigger")
c1 = [r for r in R if r["crowd1_off"] is not None]
print(f"crowd's first real buy found (to +1500) {len(c1)}/{len(R)}; offset median {stt.median(r['crowd1_off'] for r in c1)} p10 {pct([r['crowd1_off'] for r in c1], .1):.0f} p90 {pct([r['crowd1_off'] for r in c1], .9):.0f}"
      f" min {min(r['crowd1_off'] for r in c1)}; by +60 {sum(1 for r in c1 if r['crowd1_off'] <= 60)}, by +78 {sum(1 for r in c1 if r['crowd1_off'] <= 78)}, by +100 {sum(1 for r in c1 if r['crowd1_off'] <= 100)}; size median {stt.median(r['crowd1_eth'] for r in c1):.4f} ETH")
print(f"   contracts: {collections.Counter(r['crowd1_to'][:10] for r in c1).most_common(12)}")
print(f"engine's first trigger (any engine-visible buy >= 0.005) offset median {stt.median(r['eng1_off'] for r in R if r['eng1_off'] is not None)}; not the crowd's in {sum(1 for r in R if r['eng1_off'] is not None and r['eng1_off'] != r['crowd1_off'])}")
print(f"first buy >= 0.005 of anyone: who {collections.Counter(r['any1_who'] for r in R).most_common(8)}")
tr = [r["r"][KEY] for r in R]
print(f"exit ({KEY}): by the crowd's clock {sum(1 for t in tr if not t['cap'])}, at the cap {sum(1 for t in tr if t['cap'])}; trigger offset median {stt.median(t['trig_off'] for t in tr if t['trig_off'] is not None)}")
print("\n== 6. buyers before the crowd's first real buy (to +200)")
B = [(r, b) for r in R for b in r["before"]]
agg = collections.defaultdict(lambda: [0, 0.0, set(), []])
for r, b in B:
    k = ((b[2] or "")[:10], b[3]); a = agg[k]; a[0] += 1; a[1] += b[4]; a[2].add(r["pool"]); a[3].append(b[0])
for k, a in sorted(agg.items(), key=lambda kv: -kv[1][0])[:14]:
    print(f"  to {k[0]} sel {k[1]}: {a[0]} buys in {len(a[2])} pools, {a[1]:.4f} ETH, median size {a[1] / a[0]:.5f}, offsets median {stt.median(a[3])} min {min(a[3])}")
big = [(r["utc"], r["pool"][:10], b) for r, b in B if b[4] >= 0.003]
print(f"  buys of >= 0.003 ETH before the crowd: {len(big)} in {len(set(x[1] for x in big))} pools; in blocks <= +10: {sum(1 for x in big if x[2][0] <= 10)}")
for x in big[:14]: print("    ", x[0], x[1], "off", x[2][0], "from", x[2][1], "to", (x[2][2] or "")[:10], x[2][3], f"{x[2][4]:.4f} ETH", "crowd" if x[2][5] else "", "engine-visible" if x[2][6] else "")
pre = collections.Counter(sum(1 for b in r["before"] if b[0] <= 3) for r in R)
print(f"  pools by number of buys in blocks +0..+3 (ahead of or beside ours): {sorted(pre.items())}")
print("\n== 7. REPORT_W's gate (>= 100 launches at >= +4% mean, no pull before +80, >= 120 launches a day)")
for q in (0.0012, 0.0036, 0.0058):
    for e in (1, 2, 3):
        s = summ([r["r"][f"{q}|{e}|2"]["ret"] for r in R])
        print(f"  q {q} entry +{e}: n {s['n']} (>= 100: {s['n'] >= 100}), mean {s['mean']*100:+.2f}% (>= 4%: {s['mean'] >= 0.04}), pulls before +80 {sum(1 for b in bo if b <= 80)} (0: {not any(b <= 80 for b in bo)}), "
              f"{len(R) / span_d:.0f} a day (>= 120: {len(R) / span_d >= 120})")
print("\n== 8. $ a day after gas, all launches traded (no slot conflicts), entry +2, sell lands +2")
for usd in (5, 10, 15):
    qe = round(usd / EU, 4); near = min(D["stakes"], key=lambda s: abs(s - qe))
    v = [r["r"][f"{near}|2|2"]["ret"] for r in R]; per = stt.mean(v) * near * EU
    v1 = [r["r"][f"{near}|1|2"]["ret"] for r in R]; v3 = [r["r"][f"{near}|3|2"]["ret"] for r in R]
    k = max(1, round(len(v) * .1)); wo = stt.mean(sorted(v)[:-k]) * near * EU
    print(f"  ${usd} ({near} ETH = ${near*EU:.2f}): ${per:+.3f} a trade -> ${per * len(R) / span_d:+.2f} a day at {len(R) / span_d:.0f} launches a day (entry +1 ${stt.mean(v1)*near*EU*len(R)/span_d:+.2f}, +3 ${stt.mean(v3)*near*EU*len(R)/span_d:+.2f}); "
          f"without the top 10% of trades ${wo * len(R) / span_d:+.2f} a day; median trade ${stt.median(v)*near*EU:+.4f}")
print("\n== 9. the engine's dry pricing (mimic of send_sell's dry_ret: entry +2, price copy of the crowd's amount words and ETH-value buys, sells unseen, pulls not counted) vs the exact replay")
for q in (0.0058, 0.0012):
    for lab, rs in (("all", R), ("box's 24 h (Oct 11 14:23 - Oct 12 14:23 UTC)", [r for r in R if calendar.timegm((2026, 10, 11, 14, 23, 0)) <= r["ts"] < calendar.timegm((2026, 10, 12, 14, 23, 0))])):
        dr = [r["dry"][str(q)]["dry"] for r in rs]; ex = [r["r"][f"{q}|2|2"]["ret"] for r in rs]; ex1 = [r["r"][f"{q}|2|1"]["ret"] for r in rs]
        unp = [r["r"][f"{q}|2|2"]["gross_unpulled"] - (D["gas"][0] + D["gas"][1]) * BF / (q * 1e18) for r in rs]
        print(f"  q {q} {lab}: n {len(rs)}; engine dry mean {stt.mean(dr)*100:+.2f}% median {stt.median(dr)*100:+.3f}% | exact (lands +2) mean {stt.mean(ex)*100:+.2f}% median {stt.median(ex)*100:+.3f}% "
              f"| lands +1 mean {stt.mean(ex1)*100:+.2f}% | exact with pulls ignored {stt.mean(unp)*100:+.2f}%; dry > exact by more than 1 point in {sum(1 for a, b in zip(dr, unp) if a - b > 0.01)}, less in {sum(1 for a, b in zip(dr, unp) if b - a > 0.01)}")
