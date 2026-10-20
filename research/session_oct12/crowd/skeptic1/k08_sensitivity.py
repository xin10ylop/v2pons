"""Skeptic 1, step 8: how fragile the two 24 h windows' means are.
- the cap's exact block (sell at the head of + 78 .. + 82, i.e. cap send + 76 .. + 80 with landing + 2), the crowd clock unchanged;
- leave out the best 1 / 3 / 5 trades, and the Oct 12 03:00-03:30 half hour;
- the means by 6-h slice and by UTC day; the launch rate and the gaps between launches (the line's current silence);
- the top 10 trades: offset of the crowd's first engine-counted buy, the exit, and the return at each cap block."""
import json, os, statistics as st, time, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import k05_replay as K
D = json.load(open(os.path.join(HERE, "k05_rows.json"))); rows = D["rows"]; TH = D["t_head"]
fmt = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
WIN = {"recent 24 h": (TH - 86400, TH), "prior 24 h": (TH - 172800, TH - 86400), "replay window": (1791633600, 1791815412)}
HALF = (time.mktime(time.strptime("2026-10-12 03:00", "%Y-%m-%d %H:%M")) - time.timezone, time.mktime(time.strptime("2026-10-12 03:30", "%Y-%m-%d %H:%M")) - time.timezone)
CAPS = (76, 77, 78, 79, 80)
cache = {}
def ret(pool, Q, cap):
    k = (pool, Q, cap)
    if k not in cache: cache[k] = K.trade(pool, int(Q * 1e18), 2, 2, CAP_SEND=cap)["ret"]
    return cache[k]
for name, (a, b) in WIN.items():
    zs = [r for r in rows if a < r["ts"] <= b]
    print(f"\n== {name} ({fmt(a)} -> {fmt(b)} UTC), {len(zs)} launches")
    for Q in (0.0012, 0.0058):
        line = "  ".join(f"+{c + 2}: {st.mean(ret(z['pool'], Q, c) for z in zs)*100:+6.2f}%" for c in CAPS)
        print(f"  stake {Q}: mean with the cap's sell at the head of {line}")
        rs = sorted((z[f"{Q}|2"]["ret"] for z in zs), reverse=True)
        print(f"  stake {Q}: mean {st.mean(rs)*100:+.2f}%; without the best 1 {st.mean(rs[1:])*100:+.2f}%, 3 {st.mean(rs[3:])*100:+.2f}%, 5 {st.mean(rs[5:])*100:+.2f}%; "
              f"without Oct 12 03:00-03:30 ({sum(1 for z in zs if HALF[0] <= z['ts'] < HALF[1])} launches) "
              f"{st.mean(z[f'{Q}|2']['ret'] for z in zs if not HALF[0] <= z['ts'] < HALF[1])*100:+.2f}%; share of trades >= +20%: {sum(r >= .2 for r in rs)}/{len(rs)}")
    ts = sorted(z["ts"] for z in zs); gaps = sorted(((ts[i + 1] - ts[i]) / 3600, fmt(ts[i])) for i in range(len(ts) - 1))[::-1][:4]
    print(f"  longest gaps between launches: {[(round(g, 2), at) for g, at in gaps]}")
    top = sorted(zs, key=lambda z: -z["0.0058|2"]["ret"])[:10]
    print(f"  top 10 at 0.0058 (launch UTC, crowd-clock trigger offset, exit block, return at cap sell +78/+79/+80/+81/+82):")
    for z in top:
        e = z["0.0058|2"]
        print(f"    {z['utc']} {z['pool'][:10]} trig {str(e['trig']):>4} exit +{e['exit']:<3} " + " ".join(f"{ret(z['pool'], 0.0058, c)*100:+7.1f}%" for c in CAPS))
print("\n== 6-h slices (UTC) at 0.0058, landing +2 (n, mean, median)")
t0 = 1791633600
while t0 < TH:
    zs = [r for r in rows if t0 <= r["ts"] < t0 + 21600]
    if zs: print(f"  {fmt(t0)}: n {len(zs):>3} mean {st.mean(z['0.0058|2']['ret'] for z in zs)*100:+7.2f}% median {st.median(z['0.0058|2']['ret'] for z in zs)*100:+6.2f}%")
    else: print(f"  {fmt(t0)}: n   0")
    t0 += 21600
print("\n== UTC days at 0.0058 / 0.0012, landing +2")
for d0, lab in ((1791633600, "Oct 10 from 12:00"), (1791676800, "Oct 11"), (1791763200, "Oct 12 to 16:05")):
    zs = [r for r in rows if d0 <= r["ts"] < d0 + 86400 - (43200 if lab.startswith("Oct 10") else 0)]
    print(f"  {lab}: n {len(zs)} mean {st.mean(z['0.0058|2']['ret'] for z in zs)*100:+.2f}% / {st.mean(z['0.0012|2']['ret'] for z in zs)*100:+.2f}%  "
          f"median {st.median(z['0.0058|2']['ret'] for z in zs)*100:+.2f}% / {st.median(z['0.0012|2']['ret'] for z in zs)*100:+.2f}%")
