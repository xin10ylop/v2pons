"""Skeptic 1, step 6: the rule's return per window (the 24 h to the frozen head, the 24 h before, the replay's own 2.10-day window, their
'box 24 h'), and a launch-by-launch comparison with the replay analyst's r06_rows.json (same pool, stake, entry +2, landing)."""
import json, os, statistics as st, time, random
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "k05_rows.json"))); rows = D["rows"]; TH = D["t_head"]
R = {r["pool"]: r for r in json.load(open(os.path.join(HERE, "../replay/r06_rows.json")))["rows"]}
fmt = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))


def q(xs, f):
    xs = sorted(xs); k = (len(xs) - 1) * f; i = int(k); return xs[i] + (xs[min(i + 1, len(xs) - 1)] - xs[i]) * (k - i)


def summ(lab, zs, key):
    if not zs: print(f"  {lab}: none"); return
    rs = [z[key]["ret"] for z in zs]; gs = [z[key]["gross"] for z in zs]; n = len(rs); top = sorted(rs, reverse=True)[:max(1, n // 10)]
    rest = sorted(rs)[:n - len(top)]
    share = sum(top) / sum(rs) if sum(rs) > 0 else float("nan")
    pulled = sum(1 for z in zs if z[key]["pulled"])
    print(f"  {lab:<26} n {n:>3}  mean {st.mean(rs)*100:+7.2f}%  median {st.median(rs)*100:+6.2f}%  p10 {q(rs,.1)*100:+6.2f} p25 {q(rs,.25)*100:+6.2f} "
          f"p75 {q(rs,.75)*100:+6.2f} p90 {q(rs,.9)*100:+6.2f}  worst {min(rs)*100:+6.2f} best {max(rs)*100:+7.1f}  win {sum(r > 0 for r in rs)}/{n}  "
          f"top10% share {share*100:4.0f}%  mean w/o top10% {st.mean(rest)*100:+5.2f}%  gross mean {st.mean(gs)*100:+6.2f}% med {st.median(gs)*100:+5.2f}%  pulled<=sell {pulled}")


def boot(zs, key, B=4000, seed=1):
    rs = [z[key]["ret"] for z in zs]; rnd = random.Random(seed); ms = sorted(st.mean(rnd.choices(rs, k=len(rs))) for _ in range(B))
    return ms[int(.05 * B)] * 100, ms[int(.95 * B)] * 100


def pulls(lab, zs):
    p = [z["pull"] for z in zs]; offs = sorted(x["off"] for x in p if x)
    never = sum(1 for x in p if x is None)
    print(f"  {lab:<26} pulled by head {len(offs)}/{len(zs)} (never {never}); before +80 {sum(o < 80 for o in offs)}, <= +80 {sum(o <= 80 for o in offs)}, "
          f"by +100 {sum(o <= 100 for o in offs)}, by +150 {sum(o <= 150 for o in offs)}; earliest {offs[:5]}; median {st.median(offs) if offs else None}; "
          f"by launch wallet {sum(1 for x in p if x and x['by_launcher'])}; 100% of L {sum(1 for x in p if x and x['frac'] and abs(x['frac'] - 1) < 1e-9)}; "
          f"through NPM {sum(1 for x in p if x and x['to'] == '0x73991a25c818bf1f1128deaab1492d45638de0d3')}")


W = {"recent 24 h": (TH - 86400, TH), "prior 24 h": (TH - 172800, TH - 86400),
     "replay window": (1791633600, 1791815412), "their box 24 h": (1791815412 - 86400 - 420, 1791815412 - 420)}
print(f"frozen head {D['head']} at {fmt(TH)} UTC; last launch {fmt(max(r['ts'] for r in rows))} UTC; {len(D['qs1'])} WETH-token1 launches not traded")
print(f"validation: {D['val']['exact']}/{D['val']['swaps']} on-chain swaps reproduced exactly (amounts, sqrtP, L, tick)")
bf = sorted(r["basefee"] for r in rows); print(f"base fee at the launches: min {bf[0]/1e9:.4f} median {st.median(bf)/1e9:.4f} max {bf[-1]/1e9:.4f} gwei")
for name, (a, b) in W.items():
    zs = [r for r in rows if a < r["ts"] <= b]
    print(f"\n== {name}: {fmt(a)} -> {fmt(b)} UTC, {len(zs)} launches ({len(zs) / ((b - a) / 86400):.0f}/day)")
    for key in ("0.0012|2", "0.0058|2", "0.0058|1"):
        summ(f"stake {key.split('|')[0]} land +{key.split('|')[1]}", zs, key)
        if key != "0.0058|1": lo, hi = boot(zs, key); print(f"  {'':<26} bootstrap 90% interval of the mean [{lo:+.2f}, {hi:+.2f}]")
    pulls("pulls", zs)
    ex = [r["0.0058|2"] for r in zs]; print(f"  exits: cap {sum(1 for e in ex if not e['pulled'] and e['exit'] == 80)}, crowd clock {sum(1 for e in ex if not e['pulled'] and e['exit'] < 80)}")

# launch by launch against the replay analyst (their key 'stake|entry|landing')
print("\n== launch-by-launch vs the replay analyst (r06_rows.json), entry +2")
for mine, theirs in (("0.0012|2", "0.0012|2|2"), ("0.0058|2", "0.0058|2|2"), ("0.0058|1", "0.0058|2|1")):
    pairs = [(r[mine]["ret"], R[r["pool"]]["r"][theirs]["ret"], r) for r in rows if r["pool"] in R]
    d = [abs(a - b) for a, b, _ in pairs]
    big = sorted(((abs(a - b), a, b, r["utc"], r["pool"][:10]) for a, b, r in pairs), reverse=True)[:5]
    print(f"  {mine} vs {theirs}: n {len(pairs)}; |diff| <= 0.01 pt {sum(x <= 1e-4 for x in d)}, <= 0.1 pt {sum(x <= 1e-3 for x in d)}; max {max(d)*100:.3f} pt; "
          f"my mean {st.mean(a for a, _, _ in pairs)*100:+.3f}% theirs {st.mean(b for _, b, _ in pairs)*100:+.3f}%; my median {st.median(a for a, _, _ in pairs)*100:+.3f}% theirs {st.median(b for _, b, _ in pairs)*100:+.3f}%")
    for b_ in big[:3]: print(f"     largest: {b_[3]} {b_[4]} mine {b_[1]*100:+.3f}% theirs {b_[2]*100:+.3f}%")
tr = [(r["0.0058|2"]["trig"], R[r["pool"]]["r"]["0.0058|2|2"]["trig_off"]) for r in rows if r["pool"] in R]
print(f"  exit-clock trigger offset equal (or both none/after cap): {sum(1 for a, b in tr if a == b or (a is None and (b is None or b > 60)) or (b is None and a is not None and a > 60))}/{len(tr)}")
po = [((r["pull"] or {}).get("off"), R[r["pool"]]["burn_off"]) for r in rows if r["pool"] in R]
print(f"  first pull offset equal: {sum(1 for a, b in po if a == b)}/{len(po)}; differing: {[(a, b) for a, b in po if a != b][:10]}")
