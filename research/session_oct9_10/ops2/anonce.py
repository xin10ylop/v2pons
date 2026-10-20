"""nonce accounting for crowd-A wallets (incl. 0x5861, 0x20d811c8) and crowd-B wallets across the copy-loop period, cache only:
last tx sent before 83320000 (cache 83240750-83319749) vs first tx sent in 83647500-83647999 (A restart sweep) / B first sent after 83396250"""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
def sent(addrs, lo, hi):
    S = set(addrs); out = collections.defaultdict(list)
    for bn, ts, t in bc.txs(lo, hi):
        if t[1] in S: out[t[1]].append((bn, ts, t))
    return out
pre = sent(A, 83240750, 83319749)
post = sent(A, 83647500, 83647999)
mid = sent(A, 83396250, 83518499)   # cached copy-period windows + tail
gaps = collections.Counter()
for a in sorted(A):
    p = pre.get(a, []); q = post.get(a, [])
    lp = p[-1] if p else None; fq = q[0] if q else None
    g = (fq[2][4] - lp[2][4] - 1) if (lp and fq) else None
    gaps[g] += 1
    print(a[:12], lab(a), "last sent before:", (lp[0], time.strftime('%H:%M:%S', time.gmtime(lp[1])), "n%d" % lp[2][4], lp[2][2][:10], lp[2][5]) if lp else None,
          "| first sent at restart:", (fq[0], "n%d" % fq[2][4], fq[2][2][:10]) if fq else None, "| txs in between:", g, "| sent in cached copy windows:", len(mid.get(a, [])))
print("gap histogram:", gaps)
