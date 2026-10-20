"""grep the local block cache for txs touching addresses. Usage: grepc.py addr [addr...]"""
import sys, json, glob, time
W = {a.lower() for a in sys.argv[1:]}
rows = []
for f in sorted(glob.glob('/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/*.json')):
    d = json.load(open(f))
    for bn, (ts, tl) in d.items():
        for t in tl:
            if t[1] in W or t[2] in W: rows.append((int(bn), time.strftime('%m-%d %H:%M:%S', time.gmtime(ts)), t[0][:14], t[1], t[2], int(t[3]) / 1e18, t[4], t[5]))
for r in sorted(set(rows)): print(r)
