"""Stage 6: is the finder's 6% anything but the local background? 1,444-byte launches cluster near 3.0 launches, so the right null is the
rate inside the pools' own windows, not the chain-wide rate. Signals in the windows by offset from L and by line; the expected d 1..4
coverage from the local rate; the finder's own d-counts (precursor/s6_precursors.out, named key 'a 1444-byte PositionManager launch')
pooled with this slice."""
import json, collections, math
from lib import *
S = json.load(open("s1_slice.json")); P = json.load(open("s2_parsed.json"))["pools"]
sig = collections.defaultdict(list)
for r in S["launches"]:
    if r["is1444"]: sig[r["bn"]].append(r)
offs = [(b - p["L"], p["Tbn"] - b, r["line"]) for p in P for b in range(p["L"] + 1, p["Tbn"] + 1) for r in sig.get(b, [])]
print("signals inside the windows L+1..T: offset from L histogram (10-block bins):", sorted(collections.Counter(o // 10 * 10 for o, _, _ in offs).items()))
print("  by line:", collections.Counter(l for _, _, l in offs).most_common())
print("  3.0-line signals (the next 3.0 pool launched inside this pool's window): d =", sorted(d for _, d, l in offs if l == "3.0"))
gaps = [b["L"] - a["L"] for a, b in zip(P, P[1:])]
print("gaps between consecutive 3.0 launches (blocks): p10/50/90", pct(gaps, .1), pct(gaps, .5), pct(gaps, .9), "share < 60:", f"{sum(1 for g in gaps if g < 60)}/{len(gaps)}")
# local rate (blocks L+1..T-5) and the expectation
bgw = [(b, p) for p in P for b in range(p["L"] + 1, p["Tbn"] - 4)]
r_loc = sum(1 for b, p in bgw if b in sig) / len(bgw)
w14 = sum(1 for p in P if any(1 <= p["Tbn"] - b <= 4 for b in range(p["L"] + 1, p["Tbn"]) if b in sig))
e = len(P) * (1 - (1 - r_loc) ** 4)
print(f"\nthis slice: local rate {r_loc:.4f}/block -> expected pools with a signal in d 1..4: {e:.2f}; observed {w14}")
# finder's counts per d = 0..12 (from s6_precursors.out, named key)
fd = {"discovery": (133, [2, 2, 4, 1, 1, 0, 0, 1, 0, 2, 2, 2, 2], 8), "held out": (67, [2, 2, 1, 0, 1, 0, 1, 1, 1, 0, 2, 1, 0], 4)}
tot_o = w14; tot_e = e
for k, (n, c, w) in fd.items():
    r = sum(c[5:13]) / 8 / n; ex = n * (1 - (1 - r) ** 4)
    tot_o += w; tot_e += ex
    print(f"finder {k}: n {n}, d1..4 coverage {w} ({100 * w / n:.0f}%), d5..12 rate {r:.4f}/block -> expected {ex:.2f}")
p = 1 - sum(math.exp(-tot_e) * tot_e ** k / math.factorial(k) for k in range(tot_o))
print(f"pooled (finder 200 + this slice {len(P)}): observed {tot_o}, expected from each set's local rate {tot_e:.1f}; Poisson P(X >= {tot_o}) = {p:.3f}")
