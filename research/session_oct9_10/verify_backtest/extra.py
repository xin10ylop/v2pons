import sys, json, collections, statistics as st, time, math
sys.path.insert(0, '.')
from bt_mine import *
# by day, schedule margin, and where the profit comes from
day = lambda p: time.strftime("%m-%d", time.gmtime(TS[P[p]["bn"]])) if P[p]["bn"] in TS else "?"
res = {p: sim(p) for p in low}; res = {p: r for p, r in res.items() if r is not None and r['res'] in ('ok', 'pulled')}
byd = collections.defaultdict(list)
for p, r in res.items(): byd[day(p)].append(r['r'])
print("variant A by day: " + ", ".join(f"{d} n {len(v)} mean {st.mean(v):+.2%} med {st.median(v):+.2%} pos {sum(1 for a in v if a>0)/len(v):.0%}" for d, v in sorted(byd.items())))
pm = sorted(r['pull'] for r in res.values() if r['pull'] is not None)
print("scheduled pull, blocks after our buy B: min", pm[:8], "count <= 10:", sum(1 for g in pm if g <= 10), "<= 30:", sum(1 for g in pm if g <= 30), "of", len(res))
v = [r['r'] for r in res.values()]
print(f"flat trades (no crowd buy priced in, r <= -0.3%): {sum(1 for a in v if a < -0.003)}; r p5/p25/p50/p75/p95: {[round(sorted(v)[int(q*(len(v)-1))]*100,2) for q in (.05,.25,.5,.75,.95)]}")
# exit landing distribution (A: sell lands send+2; B: send+1)
for lat in (2, 1):
    ex = collections.Counter(sim(p, sell_lat=lat)['exit'] for p in res)
    print(f"sell latency {lat}: our sell lands at B+k, k: {sorted(ex.items())}")
# expected value under reaction distributions
rows = json.load(open("react_rows.json"))
hi_first = [r['gap'] for r in rows if r['fee'] >= 10000 and r['first'] and r['gap'] is not None and r['gap'] <= 30]
lo_first = [r['gap'] for r in rows if r['fee'] < 10000 and r['first'] and r['gap'] is not None and r['gap'] <= 30]
live = [5, 6, 6, 6, 7, 8, 13]
dists = {"live relay 7": live, "2-5% tier first outsider (56)": hi_first, "<1% tier first outsider (37)": lo_first, "all 100 combined": live + hi_first + lo_first}
print("\nexpected return per trade if EVERY trade draws a reaction from the distribution (pull at our buy + gap; a pull in our sell's landing block counts as a loss):")
for lat in (2, 1):
    trades = {p: sim(p, sell_lat=lat) for p in res}
    for name, gaps in dists.items():
        line = f"  sell lat {lat} | {name:32s}"
        for shift in (0, 1, 2):
            tot = []; lost = 0
            for p, r in trades.items():
                for g in gaps:
                    gg = g - shift
                    if gg <= r['exit']: tot.append(-1.0 - GAS/2/STAKE); lost += 1
                    else: tot.append(r['r'])
            line += f" | reaction {shift} blk faster: mean {st.mean(tot):+.1%}, lost {lost/len(tot):.0%}"
        print(line)
gain = st.mean(v)
print(f"\nbreak-even loss rate: mean paper gain {gain:+.2%} -> p* = g/(1+g) = {gain/(1+gain):.2%}")
for n in (7, 37, 56, 93, 100):
    print(f"   0 losses in {n} reactions: one-sided 95% upper bound on P(reaction <= exit) = {1-0.05**(1/n):.1%}")
# reaction gap by day
rr = collections.defaultdict(list)
for r in rows:
    if r['first'] and r['gap'] is not None and r['gap'] <= 30: rr[(r['fee'] < 10000, day(r['p']))].append(r['gap'])
print("\nfirst-outsider reaction gaps (<= 30 blocks) by tier and day:")
for k in sorted(rr): print(f"   {'<1%' if k[0] else '2-5%'} {k[1]}: n {len(rr[k])} min {min(rr[k])} median {st.median(rr[k])} {sorted(rr[k])}")
