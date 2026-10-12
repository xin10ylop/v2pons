"""Stage 4: the candidate measured on the slice. Signal = a block holding a 1,444-byte PositionManager launch of any line (the slice's
Initialize txs; stage 3 found no reverted or non-initialising 1,444-byte call in the windows). d = T - b (blocks before the bot's first buy).
(1) coverage: pools with a signal at d = 1..4, against the expectation from the signal's background rate; (2) the lead distribution;
(3) the rule as the engine would run it: while a 3.0 pool is open (launched, the bot's buy not yet seen), the first signal fires a buy that
lands k = 1 or 2 blocks after the signal block; it is 'useful' if it lands in T-2..T-1 (the only landing a front survives with the reaction)."""
import json, collections, math
from lib import *
S = json.load(open("s1_slice.json")); P = json.load(open("s2_parsed.json"))["pools"]
start, head = S["start"], S["head"]
L1444 = [r for r in S["launches"] if r["is1444"]]
sig = collections.defaultdict(list)
for r in L1444: sig[r["bn"]].append(r)
nblk = head - start + 1
print(f"slice {start}..{head} ({nblk} blocks, {utc(S['ts_start'])} -> {utc(S['ts_head'])} UTC); 3.0 pools {len(P)}, all with T")
print("1444-byte PositionManager launches in the slice:", len(L1444), "by line:", collections.Counter(r["line"] for r in L1444).most_common(),
      "senders distinct:", len({r['from'] for r in L1444}))
r_blk = len(sig) / nblk
print(f"background: blocks holding one {len(sig)} of {nblk} = {r_blk:.5f} per block (one every {1 / r_blk:.0f} blocks = {1 / r_blk / 9.72:.0f} s)")
# background inside the pools' own pre-T windows (L+1..T-5), the pool's own launch excluded
bgw = [(b, p) for p in P for b in range(p["L"] + 1, p["Tbn"] - 4)]
bgh = sum(1 for b, p in bgw if b in sig)
print(f"background inside the pools' windows L+1..T-5: {bgh} of {len(bgw)} blocks = {bgh / len(bgw):.5f} per block")
# (1) coverage at each d
D = {}
for p in P:
    ds = []
    for b in range(p["L"] + 1, p["Tbn"] + 1):
        for r in sig.get(b, []):
            d = p["Tbn"] - b
            if d == 0 and r["ti"] > p["Tti"]: continue          # behind the bot's tx in T's block: not a precursor
            ds.append((d, r["line"], r["from"][:10], r["ti"]))
    D[p["pid"]] = ds
cnt = [sum(1 for p in P if any(x[0] == d for x in D[p["pid"]])) for d in range(13)]
w14 = sum(1 for p in P if any(1 <= x[0] <= 4 for x in D[p["pid"]]))
w58 = sum(1 for p in P if any(5 <= x[0] <= 8 for x in D[p["pid"]]))
w912 = sum(1 for p in P if any(9 <= x[0] <= 12 for x in D[p["pid"]]))
exp14 = len(P) * (1 - (1 - r_blk) ** 4)
# binomial tail P(X >= w14 | n, p4)
p4 = 1 - (1 - r_blk) ** 4; n = len(P)
tail = sum(math.comb(n, k) * p4 ** k * (1 - p4) ** (n - k) for k in range(w14, n + 1))
print(f"\n(1) coverage: pools with a signal at d = 0..12: {cnt}")
print(f"    d 1..4: {w14} of {n} ({100 * w14 / n:.1f}%), d 5..8: {w58}, d 9..12: {w912}; expected at the background rate in any 4-block window: {exp14:.2f} "
      f"({100 * p4:.1f}%); P(X >= {w14}) = {tail:.3f}")
for p in P:
    if D[p["pid"]] and any(x[0] <= 12 for x in D[p["pid"]]):
        print(f"    pool {p['pid'][:10]} L {p['L']} T-L {p['T']}: signals at d = {[x for x in D[p['pid']] if x[0] <= 12]}")
# (2) lead distribution of every signal inside an open window
alld = [x[0] for p in P for x in D[p["pid"]]]
print(f"\n(2) every signal between L+1 and T (n {len(alld)} in {n} pools, {len(alld) / n:.2f} per pool): d histogram {sorted(collections.Counter(alld).items())}")
print(f"    share at d 1..4: {sum(1 for d in alld if 1 <= d <= 4)}/{len(alld)}; window length T-L p50 {pct([p['T'] for p in P], .5)} -> "
      f"a uniform signal puts {100 * 4 / pct([p['T'] for p in P], .5):.0f}% of its hits in d 1..4")
# (3) the rule run by the engine: first signal after L+g fires
print("\n(3) the rule as the engine runs it (the first signal while the pool is open fires; the buy lands k blocks later; useful = lands in T-2..T-1)")
res = {}
for g in (1, 16, 24):
    for k in (1, 2):
        fires = []; useful = 0; late = 0; early = 0; none = 0
        for p in P:
            bs = [b for b in range(p["L"] + g, p["Tbn"]) if b in sig and b > p["L"]]
            if not bs: none += 1; continue
            b = bs[0]; B = b + k; d = p["Tbn"] - b
            fires.append(d)
            if p["Tbn"] - 2 <= B <= p["Tbn"] - 1: useful += 1
            elif B >= p["Tbn"]: late += 1
            else: early += 1
        res[(g, k)] = dict(fires=len(fires), useful=useful, early=early, late=late, none=none)
        print(f"  gate L+{g:<2d} k={k}: fires {len(fires)} of {n} pools; useful {useful} ({100 * useful / max(1, len(fires)):.0f}% of fires, {100 * useful / n:.1f}% of pools); "
              f"too early (lands <= T-3) {early}; too late (lands >= T) {late}; no fire {none}; first-fire lead d p10/50/90 {pct(fires,.1)}/{pct(fires,.5)}/{pct(fires,.9)}")
json.dump({"D": D, "res": {f"{g},{k}": v for (g, k), v in res.items()}, "r_blk": r_blk}, open("s4_rule.json", "w"))
