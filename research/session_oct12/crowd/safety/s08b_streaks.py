"""the streak halt's threshold on the replay's chronological net returns (entry + 2, sell + 2): the longest run under +2% net, and the halts a
threshold of 8 / 12 / 16 / 20 / 25 / 30 / 40 would have given in 279 launches (each halt restarted at once). Writes s08b_streaks.out (stdout)."""
import json, os
from common import *
R = sorted(json.load(open(os.path.join(HERE, "..", "replay", "r06_rows.json")))["rows"], key=lambda r: r["ts"])
for q in ("0.002", "0.004"):
    paid = [r["r"][f"{q}|2|2"]["ret"] >= 0.02 for r in R]
    k = 0; longest = 0; runs = []
    for ok in paid:
        if ok:
            if k: runs.append(k)
            k = 0
        else: k += 1; longest = max(longest, k)
    if k: runs.append(k)
    out = []
    for th in (8, 12, 16, 20, 25, 30, 40):
        k = 0; h = 0
        for ok in paid:
            k = 0 if ok else k + 1
            if k == th: h += 1; k = 0
        out.append(f"{th}: {h}")
    print(f"{q} ETH: longest run under +2% {longest}; runs >= 8: {sum(r >= 8 for r in runs)}, >= 16: {sum(r >= 16 for r in runs)}; halts by threshold ({len(R)} launches): {', '.join(out)}")
