"""Stage 7: T - L in seconds and sub-second (block position inside its second) for every pool: headers of blocks L-15..L+15 and T-15..T+15
(no txs). Sub-second time of a block = its index among the blocks sharing its timestamp / their count. usage: s7_lsecs.py <slice>"""
import sys, pickle, collections
from lib import *
name = sys.argv[1]; kh = KV("hdr"); kb = KV("blk")
D = pickle.load(open(f"parsed_{name}.pkl", "rb")); P = [p for p in D["pools"] if p["T"] is not None]
nums = sorted(set(n for p in P for c in (p["L"], p["Tbn"]) for n in range(c - 15, c + 16) if str(n) not in kb.d))
get_blocks(nums, kh, full=False, size=50)
def ts(n):
    b = kb.d.get(str(n)) or kh.d.get(str(n)); return b["ts"] if b else None
def frac(n):
    t = ts(n); a = n; b = n
    while ts(a - 1) == t: a -= 1
    while ts(b + 1) == t: b += 1
    return t + (n - a) / (b - a + 1), b - a + 1
dt, dtb = [], []
for p in P:
    fL, nL = frac(p["L"]); fT, nT = frac(p["Tbn"]); dt.append(fT - fL); dtb.append(p["T"])
print(f"{name}: n {len(dt)}; T - L seconds (sub-second from the block's position in its second) p10/25/50/75/90",
      [round(pct(dt, q), 2) for q in (.1, .25, .5, .75, .9)], "min", round(min(dt), 2), "max", round(max(dt), 2))
print("   histogram (0.5 s bins):", sorted(collections.Counter(round(x * 2) / 2 for x in dt).items()))
best = max((sum(1 for x in dt if abs(x - m) <= 0.1) , m) for m in [i / 20 for i in range(0, 200)])
print(f"   best fixed T - L in seconds within +-0.1 s (about +-1 block): {best[0]} of {len(dt)} at {best[1]} s")
print(f"   integer-second T - L: {sorted(collections.Counter(ts(p['Tbn']) - ts(p['L']) for p in P).items())}")
