"""The bot router's ETH per hour per line (s06 bot buys joined to s14's Universal Router swaps by transaction and pool), and ETH per pool."""
import json, collections, time, bisect
from clusters import load
from common import load_jsonl, W, sgn
rows = load(); vb = {r["pid"]: r for r in rows if r["fam"].split(" (")[0] in ("VB 2.4333", "VB 3.0", "VB 5.0")}
tok2pid = {r["c1"]: r["pid"] for r in vb.values()}
bl = sorted((x["b"], x["t"]) for x in load_jsonl("s01_blocks_cache.jsonl")); bb = [b for b, _ in bl]
def t_of(b):
    i = bisect.bisect_left(bb, b); i = min(max(i, 1), len(bb) - 1); (b0, t0), (b1, t1) = bl[i - 1], bl[i]; return t0 + (t1 - t0) * (b - b0) / (b1 - b0)
sw = {}
for s in load_jsonl("s14_swaps_cache.jsonl"): sw.setdefault((s["h"], s["pid"]), []).append(s)
eth = collections.defaultdict(float); cnt = collections.Counter(); miss = 0; perpool = collections.defaultdict(float)
for x in load_jsonl("s06_bot_transfers_cache.jsonl"):
    if x["side"] != "to" or int(x["t1"], 16) == 0: continue
    pid = tok2pid.get(x["token"])
    if not pid: continue
    ss = sw.get((x["h"], pid))
    if not ss: miss += 1; continue
    a0 = sgn(W(ss[0]["d"], 0))
    fam = vb[pid]["fam"].split(" (")[0]; h = int(t_of(x["b"]) // 3600)
    eth[(fam, h)] += -a0 / 1e18; cnt[(fam, h)] += 1; perpool[pid] += -a0 / 1e18
print("bot buys not matched to a swap:", miss)
hours = sorted({k[1] for k in cnt})
print("UTC hour        " + " ".join(time.strftime("%H", time.gmtime(h * 3600)).rjust(5) for h in hours) + "   total")
for fam in ("VB 2.4333", "VB 3.0", "VB 5.0"):
    print("%-9s ETH   " % fam + " ".join(("%5.0f" % eth[(fam, h)]) for h in hours) + "  %6.0f" % sum(eth[(fam, h)] for h in hours))
print("all three ETH   " + " ".join(("%5.0f" % sum(eth[(f, h)] for f in ("VB 2.4333", "VB 3.0", "VB 5.0"))) for h in hours))
for fam in ("VB 2.4333", "VB 3.0", "VB 5.0"):
    v = sorted(perpool[p] for p, r in vb.items() if r["fam"].startswith(fam))
    print("%-9s bot ETH per pool p10/50/90 %.2f/%.2f/%.2f (n %d)" % (fam, v[len(v)//10], v[len(v)//2], v[9*len(v)//10], len(v)))
