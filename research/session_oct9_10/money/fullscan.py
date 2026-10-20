"""every block in [a, b]: all plain transactions (no calldata) with value > 0, plus every tx from/to a crowd-A wallet; streamed to a jsonl"""
import sys, json, time
from tr import *
a, b, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
f = open(out, "a"); t0 = time.time(); n = 0
for s in range(a, b + 1, 1000):
    e = min(s + 999, b)
    rows = blocks(s, e)
    for bn, t in rows:
        h, fr, to, v, nonce, sel = t
        if v > 0 and sel in ("0x", ""):
            f.write(json.dumps([bn, h, fr, to, v, nonce]) + "\n"); n += 1
    f.flush()
    for k in [k for k in BL if k < s - 2000]: del BL[k]              # keep memory flat
    print(f"{e} ({(e - a + 1) / (b - a + 1):.0%}) {n} transfers {time.time() - t0:.0f}s", flush=True)
