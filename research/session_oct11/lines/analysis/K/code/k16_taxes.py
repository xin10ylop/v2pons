"""the curve math and the extra charges, from the events: (1) replay every ETH-quoted curve's reserves from its Buy/Sell events and check each
trade's tokens against x*y=k with x0 = 1.68 ETH virtual, y0 = 1e9; (2) the extra fee (event X, inside 'fee') and the Buy's 4th word vs time
since create, buyer == creator, size."""
import json, collections, statistics as st, sys
from kload import *
C = load_creates()
ce = {k: v for k, v in C.items() if v["quote"] == 0}
maxbn = int(sys.argv[1]) if len(sys.argv) > 1 else None
T = load_trades(set(ce), maxbn)
print("ETH curves", len(ce), "with events", len(T))
err = []; xr = []; w3r = []; nB = nS = 0; bad = collections.Counter()
for c, ev in T.items():
    cr = ce[c]; x = VX0; y = Y0; xs = {}
    for r in ev:
        if r[4] == "X": xs[r[2]] = r[6][0]
    for r in ev:
        k = r[4]
        if k == "B":
            ethIn, out, fee, w3 = r[6][:4]; net = ethIn - fee - w3
            exp = y * net // (x + net)
            if out > 0: err.append(abs(exp - out) / out)
            if abs(exp - out) / max(out, 1) > 1e-6: bad["B"] += 1
            x += net; y -= out; nB += 1
            dt = r[0] - cr["bn"]
            base = ethIn // 100
            if r[2] in xs or fee > base + 1: xr.append((dt, (fee - base) / ethIn, ethIn / 1e18, r[5][1] == cr["creator"], r[2] in xs))
            if w3: w3r.append((dt, w3 / ethIn, ethIn / 1e18, r[5][1] == cr["creator"] or r[5][0] == cr["creator"], (x - VX0) / 1e18))
        elif k == "S":
            tin, eout, fee, w3 = r[6][:4]
            gross = x * tin // (y + tin)
            if gross > 0: err.append(abs(gross - (eout + fee + w3)) / gross)
            if abs(gross - (eout + fee + w3)) / max(gross, 1) > 1e-6: bad["S"] += 1
            x -= gross; y += tin; nS += 1
print("buys", nB, "sells", nS, "model mismatches >1e-6", bad, "median rel err", st.median(err) if err else None, "p99", sorted(err)[int(len(err) * 0.99)] if err else None)
print("extra-fee buys", len(xr))
by = collections.defaultdict(list)
for dt, rate, eth, isc, hasx in xr: by[min(dt // 5 * 5, 200)].append(rate)
for k in sorted(by)[:30]: print("  dt", k, "n", len(by[k]), "rate median", round(st.median(by[k]) * 1e4, 1), "bps min", round(min(by[k]) * 1e4, 1), "max", round(max(by[k]) * 1e4, 1))
print("w3 buys", len(w3r), "creator share", sum(1 for z in w3r if z[3]) / max(1, len(w3r)))
for z in sorted(w3r, key=lambda z: z[2])[:: max(1, len(w3r) // 25)]: print("   dt", z[0], "rate bps", round(z[1] * 1e4, 1), "eth", z[2], "creator", z[3], "real after", round(z[4], 4))
