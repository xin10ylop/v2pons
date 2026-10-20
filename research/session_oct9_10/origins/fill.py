"""Fill the shared 250-block cache (ops/lch/bc) for ranges, one process, with pauses; optional stop-condition: an incoming value tx to ADDR.
usage: fill.py lo hi [backward|forward] [stop_addr]"""
import sys, os, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
import bc
lo, hi = int(sys.argv[1]), int(sys.argv[2]); direction = sys.argv[3] if len(sys.argv) > 3 else "forward"; stop = sys.argv[4].lower() if len(sys.argv) > 4 else None; side = sys.argv[5] if len(sys.argv) > 5 else "to"
cs = list(range(lo // bc.CH, hi // bc.CH + 1))
if direction == "backward": cs = cs[::-1]
for c in cs:
    for k in range(8):
        try: d = bc.chunk(c); break
        except Exception as e: print("retry", c, e, flush=True); time.sleep(15 * (k + 1))
    else: print("FAILED chunk", c, flush=True); continue
    hit = []
    if stop:
        for bn, (ts, tl) in d.items():
            for t in tl:
                if side == "to" and t[2] == stop and int(t[3]) > 0: hit.append((bn, t[1], int(t[3]) / 1e18, t[4]))
                if side == "from" and t[1] == stop: hit.append((bn, t[2], int(t[3]) / 1e18, t[4], t[5]))
    print(time.strftime("%H:%M:%S"), "chunk", c * bc.CH, bc.STATS, ("HIT " + str(hit)) if hit else "", flush=True)
    if hit: break
print("done", flush=True)
