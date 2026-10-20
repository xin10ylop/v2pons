"""Scan block windows (via the shared ops/lch/bc.py block cache) and write every value>0 tx to a jsonl:
[bn, ts, hash, from, to, value_wei, nonce, sel]. Usage: winscan.py windows.json out.jsonl"""
import sys, json, os, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins")
import fb as bc
W = json.load(open(sys.argv[1])); out = sys.argv[2]
W = sorted(W); merged = []
for a, b in W:
    if merged and a <= merged[-1][1] + 1: merged[-1][1] = max(merged[-1][1], b)
    else: merged.append([a, b])
tot = sum(b - a + 1 for a, b in merged); print(tot, "blocks in", len(merged), "windows", flush=True)
done = 0; t0 = time.time(); seen = set()
if os.path.exists(out):
    for l in open(out): seen.add(json.loads(l)[2])
f = open(out, "a")
for a, b in merged:
    for s in range(a, b + 1, 250):
        e = min(b, s + 249)
        for bn, ts, t in bc.txs(s, e):
            if int(t[3]) > 0 and t[0] not in seen:
                seen.add(t[0]); f.write(json.dumps([bn, ts, t[0], t[1], t[2], t[3], t[4], t[5]]) + "\n")
        f.flush(); done += e - s + 1
        print(f"{done}/{tot} blocks, through {e}, {time.time() - t0:.0f}s, req {bc.STATS}", flush=True)
