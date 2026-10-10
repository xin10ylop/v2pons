import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
R = json.load(open(os.path.join(HERE, "timeline.json")))
# 1. outsiders before the first crowd buy
pre = []
for r in R:
    for x in r["swaps"]:
        if x["off"] >= r["crowd1"]: break
        if x["buy"] and x["cls"] not in ("crowd", "dust"):
            pre.append((x["off"], r["crowd1"], round(x["eth"], 7), x["cls"], x["from"], x["to"], x["sel"], x["len"]))
c = collections.Counter((p[3], p[5], p[6]) for p in pre); print("pre-crowd buys by cls/to/sel", c.most_common())
print("pre-crowd buys >= 0.0002", [p for p in pre if p[2] >= 0.0002])
print("max pre-crowd outsider", max(p[2] for p in pre))
# 2. other buyers (not crowd/dust/sniper), anywhere fetched
oth = collections.defaultdict(list)
for r in R:
    for x in r["swaps"]:
        if x["cls"] == "other" and x["buy"]:
            oth[(x["from"], x["to"], x["sel"], x["len"])].append((x["off"], round(x["eth"], 6), r["crowd1"], r["pull"]))
for k, v in sorted(oth.items(), key=lambda kv: -len(kv[1]))[:25]:
    print(len(v), k, "off q", q([a[0] for a in v], (0, .5, 1)), "eth q", q([a[1] for a in v], (0, .5, 1)), "relative to crowd1 min", min(a[0] - a[2] for a in v))
# 3. each pull: what preceded it
print("\n--- pulls")
pl_rows = []
for r in R:
    if r["pull"] is None: continue
    P_ = r["pull"]
    before = [x for x in r["swaps"] if x["off"] <= P_]
    last_crowd = max([x["off"] for x in before if x["cls"] == "crowd" and x["buy"]], default=None)
    oth_b = [(x["off"], round(x["eth"], 6), x["cls"], x["from"][:10] if x["from"] else None) for x in before if x["buy"] and x["cls"] not in ("crowd", "dust") and x["off"] >= P_ - 60]
    sells = [(x["off"], round(x["eth"], 4), x["cls"]) for x in before if not x["buy"] and x["off"] >= P_ - 60]
    ethin = sum(x["eth"] for x in before if x["buy"]) - sum(x["eth"] for x in before if not x["buy"])
    pl_rows.append((P_, r["add_value"], r["crowd1"], last_crowd, P_ - last_crowd if last_crowd is not None else None, round(ethin, 3), oth_b, sells))
for x in sorted(pl_rows): print(x)
