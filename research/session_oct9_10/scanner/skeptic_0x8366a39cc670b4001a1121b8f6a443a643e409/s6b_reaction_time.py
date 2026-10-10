import sys, os, datetime; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
R = json.load(open(os.path.join(HERE, "timeline.json")))
ev = []
for r in R:
    for x in r["swaps"]:
        if x["buy"] and x["cls"] == "other" and x["eth"] >= 0.0001 and (r["pull"] is None or x["off"] <= r["pull"]):
            d = (r["pull"] - x["off"]) if r["pull"] is not None else None
            full = x["off"] <= 590 or (r["pull"] is not None and x["off"] >= r["pull"] - 80)
            ev.append((r["ts"], datetime.datetime.utcfromtimestamp(r["ts"]).strftime("%m-%d %H:%M"), x["off"], round(x["eth"], 6), x["from"][:10], x["to"][:10], x["len"], d, r["add_value"], r["crowd1"], full))
for e in sorted(ev): print(e[1:])
# launches by hour
hrs = collections.Counter(datetime.datetime.utcfromtimestamp(r["ts"]).strftime("%m-%d %H") for r in R)
print(sorted(hrs.items()))
