import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
R = json.load(open(os.path.join(HERE, "timeline.json")))
for r in sorted(R, key=lambda r: (r["pull"] is None, r["pull"] or 0)):
    if r["pull"] is None or r["pull"] > 600: continue
    o = [(x["off"], "%.1e" % x["eth"], x["cls"][:2], (x["from"] or "")[2:8]) for x in r["swaps"] if x["buy"] and x["cls"] not in ("crowd", "dust") and x["off"] <= r["pull"]]
    os_ = [(x["off"], "%.1e" % x["eth"], x["cls"][:2]) for x in r["swaps"] if not x["buy"] and x["cls"] != "crowd" and x["off"] <= r["pull"]]
    print(r["pull"], "c1", r["crowd1"], "v", r["add_value"], "buys:", o, "sells:", os_)
