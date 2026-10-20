import sys, json, collections, statistics as st, time
sys.path.insert(0, '.')
exec(open('react.py').read().split("ops = sorted")[0])
ops = sorted([p for p in P if launcher[p] == OP], key=lambda p: P[p]["bn"])
day = lambda p: time.strftime("%m-%d %H", time.gmtime(TS[P[p]["bn"]]))
rows = json.load(open("react_rows.json"))
rr = collections.defaultdict(list)
for r in rows:
    if r['first'] and r['gap'] is not None and r['gap'] <= 30: rr[(r['fee'] < 10000, day(r['p'])[:5])].append(r['gap'])
print("first-outsider reaction gaps (<= 30 blocks) by tier and day:")
for k in sorted(rr): print(f"   {'<1%' if k[0] else '2-5%'} {k[1]}: n {len(rr[k])} min {min(rr[k])} median {st.median(rr[k])} {sorted(rr[k])}")
# sub-1% launches: who made the first real buy, and the pull gap from it
low = [p for p in ops if P[p]['fee'] < 10000]
c = collections.Counter(); notcrowd = []
for p in low:
    b0 = P[p]['bn']; R = [z for z in roles(p) if z[0][3] < 0 and -z[0][3] >= 2e14 and z[0][0] > b0]
    if not R: continue
    x, ro, w, t = R[0]; c[ro] += 1
    rems = sorted(z[0] for z in L.get(p, []) if z[5] < 0)
    if ro not in ('fresh', 'wash'): notcrowd.append((day(p), p[:12], ro, round(-x[3]/1e18, 4), x[0]-b0, (rems[0]-x[0]) if rems else None))
print("sub-1%: role of the first real-size buy (our trigger):", dict(c))
for z in notcrowd: print("   not the crowd:", z, "(day, pool, role, ETH, offset, pull gap from it)")
# the launch with the scheduled pull at B+5
for p in low:
    b0 = P[p]['bn']
    if b0 == 79348602:
        for x, ro, w, t in roles(p): print(f"   10-03 launch: +{x[0]-b0} {ro} {'buy' if x[3]<0 else 'sell'} {abs(x[3])/1e18:.5f} w {w[:10]} nonce {t[2]}")
        print("   liquidity:", [(z[0]-b0, z[5] > 0) for z in L[p]])
