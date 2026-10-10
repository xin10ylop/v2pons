"""Pull rate by outsider exposure. Exposure window: add+0..+200 (full tx coverage). Outsider = any buy not crowd, dust or the sniper."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
R = json.load(open(os.path.join(HERE, "timeline.json")))
W = 200
def cat(r):
    o = [x for x in r["swaps"] if x["buy"] and x["cls"] == "other" and x["off"] <= W and (r["pull"] is None or x["off"] < r["pull"])]
    m = max((x["eth"] for x in o), default=0)
    pair = any(x["from"] in ("0x57ee6646fe8748dc8c10ac96caae7ce2373ede5d", "0xf05d0e3f4b7777223e132254a1dc12127d503384") for x in o)
    sn = any(x["cls"] == "sniper" and x["buy"] for x in r["swaps"] if x["off"] <= W)
    return ("none" if m == 0 else "<1e-4" if m < 1e-4 else ">=1e-4"), pair, sn
tab = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for r in R:
    c, pair, sn = cat(r)
    for key in [("size", c), ("pair57ee/f05d", pair), ("sniper", sn)]:
        t = tab[key]; t[0] += 1
        p = r["pull"]
        t[1] += p is not None and p <= 240; t[2] += p is not None and p <= 600; t[3] += p is not None; t[4] += p is not None and p <= 180
for k, v in sorted(tab.items(), key=str): print(k, "n", v[0], "pulled<=180", v[4], "<=240", v[1], "<=600", v[2], "<=3000", v[3])
# the pair's activity: pools with the pair, pull offset minus the pair's first buy
d = []
for r in R:
    o = [x for x in r["swaps"] if x["buy"] and x["from"] in ("0x57ee6646fe8748dc8c10ac96caae7ce2373ede5d", "0xf05d0e3f4b7777223e132254a1dc12127d503384")]
    if o: d.append((o[0]["off"], r["pull"] - o[0]["off"] if r["pull"] is not None and r["pull"] >= o[0]["off"] else None))
print("pair pools", len(d), "pair first buy off q", q([a for a, b in d], (0, .1, .5, .9, 1)), "delay to pull", sorted(b for a, b in d if b is not None))
