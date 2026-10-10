"""for every launch since 09:00: the 450 blocks before it (sweep -> dispatcher -> this deployer) and the 450 after its pull (deployer -> sweep);
plain transfers written to win.jsonl; blocks already in part*.jsonl ranges are skipped"""
import json, sys, glob, time
RESUME = int(sys.argv[1]) if len(sys.argv) > 1 else 0
from tr import *
L = json.load(open("launches_now.json"))
spans = []
for x in L:
    spans.append((x["block"] - 450, x["block"]))
    if x["pull"]: spans.append((x["pull"], x["pull"] + 450))
spans.sort(); merged = []
for a, b in spans:
    if merged and a <= merged[-1][1] + 1: merged[-1][1] = max(merged[-1][1], b)
    else: merged.append([a, b])
print(sum(b - a + 1 for a, b in merged), "blocks in", len(merged), "windows", flush=True)
f = open("win.jsonl", "a"); done = 0
for a, b in merged:
    for s in range(a, b + 1, 300):
        e = min(s + 299, b)
        if e <= RESUME: done += e - s + 1; continue
        for k in range(8):
            try:
                rows = blocks(s, e); break
            except Exception as ex:
                print("retry", s, ex, flush=True); time.sleep(10 * (k + 1))
        for bn, t in rows:
            h, fr, to, v, nonce, sel = t
            if v > 0 and sel in ("0x", ""): f.write(json.dumps([bn, h, fr, to, v, nonce]) + "\n")
        f.flush(); done += e - s + 1
        for k in [k for k in BL if k < s]: del BL[k]
        print(done, e, flush=True)
