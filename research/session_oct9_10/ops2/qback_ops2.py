"""fetch chunks backward from hi until an incoming plain transfer to addr appears (one process, gentle). usage: qback_ops2.py addr hi lo"""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
x, hi, lo = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]); t0 = time.time()
for c in range(hi // bc.CH, lo // bc.CH - 1, -1):
    d = bc.chunk(c); bc._mem.clear()
    rs = [R(bn, d[bn][0], t) for bn in sorted(d) for t in d[bn][1] if t[2] == x or t[1] == x]
    for r in rs: print(fmt(r), lab(r["from"]), "->", lab(r["to"]), flush=True)
    if any(r["to"] == x and r["eth"] > 0.01 for r in rs): print("found at chunk", c * bc.CH, f"{time.time() - t0:.0f}s", bc.STATS, flush=True); break
    print("chunk", c * bc.CH, "none", f"{time.time() - t0:.0f}s", flush=True)
