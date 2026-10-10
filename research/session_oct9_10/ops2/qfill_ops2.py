"""fill the shared block cache for [lo, hi] chunk by chunk (one process, gentle_post: <=50 per batch, backoff on 429/errors)"""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
lo, hi = int(sys.argv[1]), int(sys.argv[2])
m = missing(lo, hi); t0 = time.time()
print(len(m), "chunks to fetch", flush=True)
for i, c in enumerate(m):
    bc.chunk(c); bc._mem.clear()
    if i % 10 == 0: print(i, c * bc.CH, f"{time.time() - t0:.0f}s", bc.STATS, flush=True)
print("done", bc.STATS, flush=True)
