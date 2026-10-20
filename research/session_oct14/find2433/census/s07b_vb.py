"""VB 3.0 / 5.0 samples: the bot router's first buy offset and the pull, split by launch-wallet type (fresh vs high nonce) and 6-hour block.
Output: s07b_vb.out."""
from common import *
import collections
import s07_traits as S
tg = jload("s05_targets.json"); A = "0x1cbaf24d:0xc1120e3d"
def q(xs, f):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None
def pct(xs): return "%s/%s/%s" % (q(xs, .1), q(xs, .5), q(xs, .9)) if xs else "-"
for fam in ("SAMPLE VB 3.0", "SAMPLE VB 5.0"):
    g = collections.defaultdict(lambda: dict(T=[], pull=[], n=0, early=0, nb=[]))
    for t in tg:
        if t["fam"] != fam: continue
        r = S.rows[t["pid"]]; p = S.EV[t["pid"]]; sw = S.swaps(p, r); pl, _ = S.pulls(p)
        T = next((s["bn"] - r["b"] for s in sw if s["buy"] and s["bn"] - r["b"] <= 80 and S.actor(s["h"]) == A), None)
        typ = "fresh" if r["n"] < 50 else "highnonce"; blk = time.strftime("%d %H", time.gmtime(r["t"] - r["t"] % 21600))
        for k in ((typ, "all"), (typ, blk)):
            d = g[k]; d["n"] += 1
            if T is not None: d["T"].append(T); d["early"] += T <= 20
            if pl: d["pull"].append(pl[0] - r["b"])
            d["nb"].append(sum(1 for s in sw if s["buy"] and (s["eth"] or 0) >= 0.01))
    print("==", fam)
    for k in sorted(g):
        d = g[k]
        print("  %-10s %-6s n %3d  bot first buy %s (<= +20: %d)  pull %s  big buys in +4000 %s" % (k[0], k[1], d["n"], pct(d["T"]), d["early"], pct(d["pull"]), pct(d["nb"])))
