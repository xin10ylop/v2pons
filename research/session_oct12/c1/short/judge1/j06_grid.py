"""Judge 1: trigger max_blocks x hold grid (engine-exact fills, $5 per attempt, 95% pool bootstrap), with the two margins:
  lag axis: the fastest reaction lag seen from a holder's buy (36, ours) minus the landing (buy + hold + 2);
  age axis: the earliest pull of a triggered pool (L+147; L+133 for a pool with no trigger) minus the latest landing age (max_blocks + 2 + hold + 2);
  data: the earliest pull after our would-be buy among the pools the setting triggers (filled or not)."""
from j02_sim import *
pools, head = load_pools()
line = [p for p in pools if p["shape"] == "line"]
stake = 2 * 10 ** 15
HOLDER = ("ours", "holder-pre", "holder-early", "holder-later", "bd13")
EX = ["hold 20", "hold 25", "hold 30", "tp 4% cap 30", "tp 6% cap 30"]
print(" mb    exit           (a) holder: n  fills  $/att [CI]                (b) all: n  fills  $/att [CI]             pulled a/b   margin lag / age / data")
for mb in (100, 113, 125, 150, 200, 400):
    rows = run(line, stake, mb)
    first_pull = min((r["pull_after_buy"] for r in rows if r["pull_after_buy"] is not None), default=None)
    for ex in EX:
        n = int(ex.split()[-1])
        A = [r for r in rows if r["reg"] in HOLDER]
        va = [usd(r, ex, stake) for r in A]; vb = [usd(r, ex, stake) for r in rows]
        la, ha = boot(va); lb, hb = boot(vb)
        pa = sum(1 for r in A if r["fill"] and r["res"][ex][1]); pb = sum(1 for r in rows if r["fill"] and r["res"][ex][1])
        print(f" {mb:3d}   {ex:13s}  {len(A):3d} {sum(r['fill'] for r in A):3d}  {sum(va) / len(va):+.3f} [{la:+.3f}, {ha:+.3f}]      {len(rows):3d} {sum(r['fill'] for r in rows):3d}  {sum(vb) / len(vb):+.3f} [{lb:+.3f}, {hb:+.3f}]"
              f"     {pa}/{pb}      {36 - (n + 2):+3d} / {147 - (mb + 2 + n + 2):+4d} / {first_pull - (n + 2):+4d}")
