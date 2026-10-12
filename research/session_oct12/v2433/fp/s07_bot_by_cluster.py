"""The volume bot router's buys (s06: token Transfers PoolManager -> router) and its token mints (0x0 -> router), per hour per launch cluster
(the token's pool from s03; tokens of pools launched before Oct 11 18:00 are 'pre-window'). Also its first and last buy per cluster.
A PoolManager -> router transfer is a buy when its transaction holds a Universal Router swap of that line (s14), else a pull through the router."""
import json, collections, time, bisect
from clusters import load
from common import load_jsonl
rows = load(); E = "0x" + "0" * 40
tok = {}
for r in rows:
    t = r["c1"] if r["c0"] == E else r["c1"]
    tok.setdefault(r["c1"], r); tok.setdefault(r["c0"], r) if r["c0"] != E else None
bl = sorted((x["b"], x["t"]) for x in load_jsonl("s01_blocks_cache.jsonl")); bb = [b for b, _ in bl]
def t_of(b):
    i = bisect.bisect_left(bb, b); i = min(max(i, 1), len(bb) - 1); (b0, t0), (b1, t1) = bl[i - 1], bl[i]; return t0 + (t1 - t0) * (b - b0) / (b1 - b0)
tr = [x for x in load_jsonl("s06_bot_transfers_cache.jsonl") if x["side"] == "to"]
urtx = {s["h"] for s in load_jsonl("s14_swaps_cache.jsonl")}   # a PoolManager -> router transfer with no Universal Router swap in its tx is a pull (0xa0f7978d), not a buy
hours = list(range(int(bl[0][1] // 3600), int(bl[-1][1] // 3600) + 1))
tab = collections.defaultdict(collections.Counter); first = {}; last = {}; toks = collections.defaultdict(set)
for x in tr:
    r = tok.get(x["token"])
    kind = "mint" if int(x["t1"], 16) == 0 else "buy" if x["h"] in urtx else "pull" if r else "buy+pull (not split)"; fam = r["fam"] if r else "pre-window pool (launched before Oct 11 18:00)"
    k = (kind, fam); tm = t_of(x["b"])
    tab[k][int(tm // 3600)] += 1; first[k] = min(first.get(k, 9e18), tm); last[k] = max(last.get(k, 0), tm); toks[k].add(x["token"])
print("UTC hour  " + " ".join(time.strftime("%H", time.gmtime(h * 3600)) .rjust(4) for h in hours))
for k in sorted(tab, key=lambda k: (k[0], -sum(tab[k].values()))):
    print("%-4s %-44s n %6d tokens %4d  %s..%s" % (k[0], k[1][:44], sum(tab[k].values()), len(toks[k]), time.strftime("%d %H:%M", time.gmtime(first[k])), time.strftime("%d %H:%M", time.gmtime(last[k]))))
    print("          " + " ".join(str(tab[k][h]).rjust(4) for h in hours))
