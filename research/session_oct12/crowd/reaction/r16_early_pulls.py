"""logs only: the line's earliest pulls (first Burn with liquidity), with the + 1 bot's presence and the first buy >= 0.005 ETH; the pull
offset histogram; and how many pulls land within a few blocks after our cap (+ 80) - the margin a late sell would eat."""
from common import *
import collections
from wcommon import compact
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
pulls = []
for e in jl(J("r02_events_cache.jsonl")):
    x = L.get(e["pool"])
    if not x: continue
    lb = x["lb"]; qs = x["qs"]
    ev = [c for c in (compact(l) for l in e["logs"]) if c]
    pl = [c[1] - lb for c in ev if c[0] == "b" and c[8] > 0]
    if not pl: pl = [c[1] - lb for c in (compact(l) for l in (B.get(x["pool"]) or {}).get("burns", [])) if c and c[8] > 0]
    if not pl: continue
    p = min(pl); bot = any(c[0] == "s" and c[5].startswith("0x570759db") and c[1] - lb <= 2 for c in ev)
    fb = [c[1] - lb for c in ev if c[0] == "s" and (c[7] if qs == 0 else c[8]) >= 5e15 and c[1] - lb >= 2]
    f = min(fb) if fb else None
    sell = min(f + 20, 80) if f is not None else 80
    pulls.append((p, bot, f, sell, utc(x["ts"])))
pulls.sort(key=lambda r: (r[0], r[4]))
print(f"{len(pulls)} pulled pools of {len(L)}")
print("earliest 30 pulls: offset, +1 bot present, first buy >= 0.005 at/after +2 (None: none before), our sell's landing block, launch UTC")
for r in pulls[:30]: print("  ", r)
c = collections.Counter(min(p // 10 * 10, 300) for p, *_ in pulls)
print("pull offsets, 10-block bins:", sorted(c.items())[:20])
print("pulled at or before our sell:", sum(1 for p, b, f, s, t in pulls if p <= s))
for m in (1, 3, 5, 10, 20):
    print(f"  pulled within {m:>2} blocks after our sell's block (a sell landing {m} blocks late would be caught): {sum(1 for p, b, f, s, t in pulls if s < p <= s + m)}"
          f"  (of which no crowd trigger: {sum(1 for p, b, f, s, t in pulls if s < p <= s + m and f is None)})")
