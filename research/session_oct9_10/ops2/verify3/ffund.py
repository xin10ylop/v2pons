"""find who funded F-seed deployer 0x8a10f14e before its launch (blk 81255830): gentle backward block scan, stop when found"""
from vlib import fetch_range, touching
A = "0x8a10f14e609e6df253b2a34b3739e3cc2d7f0e98"
hi = 81255830
for lo in range(hi - 250, hi - 3001, -250):
    r = touching([A], lo, lo + 249)
    print("scanned", lo, lo + 249, "hits", len(r), flush=True)
    for x in r: print("  ", x[0], x[1], x[2], "->", x[3], x[4] / 1e18, "n", x[5], x[6], flush=True)
    if any(x[3] == A for x in r): break
