"""crowd A (32 wallets): last tx sent before 83385500 and first tx sent at/after 83647500, over every cached block (no RPC);
nonce difference - 1 = number of txs they sent in between (whether cached or not)"""
import os, json, sys, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from labels import A, lab
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
pre = {}; post = {}; mid = collections.defaultdict(list); seen = set()
for f in sorted(os.listdir(D)):
    if not f.endswith(".json"): continue
    try: d = json.load(open(D + f))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen or bn < 83240750 or bn > 83700000: continue
        seen.add(bn)
        for t in tl:
            if t[1] in A:
                if bn < 83385500 and (t[1] not in pre or bn > pre[t[1]][0]): pre[t[1]] = (bn, ts, t[4], t[2], t[5])
                if bn >= 83647500 and (t[1] not in post or bn < post[t[1]][0]): post[t[1]] = (bn, ts, t[4], t[2], t[5])
                if 83385500 <= bn < 83647500: mid[t[1]].append((bn, t[4], t[2]))
g = collections.Counter(); lastt = []
for a in sorted(A):
    p, q = pre.get(a), post.get(a)
    gap = (q[2] - p[2] - 1) if p and q else None; g[gap] += 1
    if p: lastt.append(p[1])
    print(a[:12], lab(a), "last before: blk %s %s n%s -> %s %s" % (p[0], time.strftime("%H:%M:%S", time.gmtime(p[1])), p[2], p[3][:10], p[4]) if p else None,
          "| first at restart: blk %s n%s -> %s" % (q[0], q[2], q[3][:10]) if q else None, "| txs between:", gap, "| cached txs between:", len(mid.get(a, [])))
print("gap histogram", g, "latest 'last before' time", time.strftime("%H:%M:%S", time.gmtime(max(lastt))) if lastt else None, "blocks", len(seen))
