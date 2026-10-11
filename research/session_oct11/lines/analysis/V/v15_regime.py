"""Regime: per day (launch time; day 6 = the last 24 h, Oct 10 13:52 - Oct 11 13:52 UTC) launches, triggered share, the trigger's offset,
the bot's first-buy size, the follow trade (T+2, hold 60) and its tails; hour by hour over the last 24 h; the longest gap with no launch
and with no bot trigger."""
import pickle, datetime
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
Q = int(0.0058e18)
g = {x["pid"]: x for x in R["grid"]["2|60"]}
def ret(pid):
    x = g[pid]; return -1.0 if x["pulled_le"] else x["ret"]
byday = C.defaultdict(list)
for pid, r in rows.items(): byday[day_of(r["launch_ts"])].append(pid)
print("day (UTC start) | launches | triggered | trigger offset p10/50/90 | bot first buy ETH med | trade n mean med win lost | trimmed mean (drop top 5%) | pulled share (3000 blocks)")
for d in sorted(byday):
    ps = byday[d]; tr = [p for p in ps if p in R["trig"]]
    offs = [R["trig"][p][0] - rows[p]["launch_block"] for p in tr]; sz = [R["trig"][p][4] / 1e18 for p in tr]
    rs = sorted(ret(p) for p in tr); k = int(len(rs) * 0.95)
    start = datetime.datetime.utcfromtimestamp(T0 + 86400 * d).strftime("%m-%d %H:%M")
    print(f"d{d} {start} | {len(ps):4d} | {len(tr):4d} ({len(tr)/len(ps):.0%}) | {p3(offs)} | {pct(sz,0.5):.3f} | {len(rs)} {sum(rs)/len(rs):+.4f} {pct(rs,0.5):+.4f} {sum(1 for v in rs if v>0)/len(rs):.0%} {sum(1 for v in rs if v==-1)/len(rs):.1%} | {sum(rs[:k])/k:+.4f} | {sum(1 for p in ps if rows[p]['n_pulls'])/len(ps):.0%}")
print("\nlast 24 h, hour by hour (hour index from Oct 10 13:52 UTC): launches, triggered, trade mean/median, lost")
t6 = T0 + 6 * 86400
for h in range(24):
    ps = [p for p, r in rows.items() if t6 + 3600 * h <= r["launch_ts"] < t6 + 3600 * (h + 1)]
    tr = [p for p in ps if p in R["trig"]]; rs = [ret(p) for p in tr]
    hs = datetime.datetime.utcfromtimestamp(t6 + 3600 * h).strftime("%m-%d %H:%M")
    print(f"  h{h:02d} {hs} launches {len(ps):3d} triggered {len(tr):3d} " + (f"mean {sum(rs)/len(rs):+.3f} med {pct(rs,0.5):+.3f} lost {sum(1 for v in rs if v==-1)}" if rs else ""))
ts = sorted(r["launch_ts"] for r in rows.values()); gaps = sorted(((b - a) / 3600, datetime.datetime.utcfromtimestamp(a).strftime("%m-%d %H:%M")) for a, b in zip(ts, ts[1:]))[-5:]
print("\nlongest gaps between launches (h, from):", [(round(a, 2), b) for a, b in gaps])
tts = sorted(rows[p]["launch_ts"] for p in R["trig"]); gaps = sorted(((b - a) / 3600, datetime.datetime.utcfromtimestamp(a).strftime("%m-%d %H:%M")) for a, b in zip(tts, tts[1:]))[-5:]
print("longest gaps between triggered launches (h, from):", [(round(a, 2), b) for a, b in gaps])
print("last C-1 launch in the census:", max(r["launch_utc"] for r in rows.values()))
# the 6 sqrt/L variants
print("launch shape variants (sqrt_p0, mint L):", C.Counter((r["sqrt_p0"], Pool(r, E[p]).L0) for p, r in rows.items()).most_common(8))
