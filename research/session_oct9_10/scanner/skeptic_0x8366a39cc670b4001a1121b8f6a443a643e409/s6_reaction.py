"""Does the launch wallet pull right after an outsider's buy? Full tx coverage only within add+600 (every swap there was fetched),
so the test uses outsider buys at add+0..+590 and the pull delay after them; baseline = the pull hazard at random offsets."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
import random
R = json.load(open(os.path.join(HERE, "timeline.json")))
out = {}
# sniper sizes
sn = [x["eth"] for r in R for x in r["swaps"] if x["cls"] == "sniper" and x["buy"]]
print("sniper buys", len(sn), "min/max", min(sn), max(sn), ">=1e-4:", sum(1 for v in sn if v >= 1e-4))
out["sniper_buy_eth_min_max"] = [min(sn), max(sn), sum(1 for v in sn if v >= 1e-4)]
for thr in (0.00005, 0.0001, 0.0002, 0.0005):
    ev = []
    for r in R:
        firsts = [x for x in r["swaps"] if x["buy"] and x["cls"] == "other" and x["eth"] >= thr and x["off"] <= 590 and (r["pull"] is None or x["off"] <= r["pull"])]
        if not firsts: continue
        x = firsts[0]
        d = (r["pull"] - x["off"]) if r["pull"] is not None else None
        ev.append({"off": x["off"], "eth": round(x["eth"], 6), "from": x["from"], "to": x["to"], "delay": d, "crowd1": r["crowd1"], "pid": r["pid"][:12]})
    w = lambda k: sum(1 for e in ev if e["delay"] is not None and e["delay"] <= k)
    print(f"thr {thr}: pools with an outsider buy (first, <= +590) {len(ev)}; pulled within 6 blocks {w(6)}, 10 {w(10)}, 20 {w(20)}, 60 {w(60)}")
    out[f"thr_{thr}"] = {"n": len(ev), "pull_le6": w(6), "pull_le10": w(10), "pull_le20": w(20), "events": ev}
    if thr == 0.0001:
        for e in sorted(ev, key=lambda e: e["off"]): print("   ", e)
# baseline: random (pool, offset in 68..590) not followed by an outsider buy in the prior 20 blocks: P(pull within 6 / 10)
random.seed(1); hits6 = hits10 = n = 0
for _ in range(200000):
    r = random.choice(R); o = random.randint(68, 590)
    if r["pull"] is not None and r["pull"] < o: continue
    if any(x["buy"] and x["cls"] == "other" and x["eth"] >= 0.0001 and o - 20 <= x["off"] <= o for x in r["swaps"]): continue
    n += 1
    if r["pull"] is not None and r["pull"] - o <= 6: hits6 += 1
    if r["pull"] is not None and r["pull"] - o <= 10: hits10 += 1
print("baseline P(pull within 6) %.4f, within 10 %.4f (n %d)" % (hits6 / n, hits10 / n, n))
out["baseline"] = {"p6": hits6 / n, "p10": hits10 / n, "n": n}
# delay of pulls after outsider buys vs after crowd buys
d_cr = []
for r in R:
    if r["pull"] is None: continue
    lc = [x["off"] for x in r["swaps"] if x["cls"] == "crowd" and x["buy"] and x["off"] <= r["pull"]]
    d_cr.append(r["pull"] - lc[-1] if lc else None)
print("pull delay after the last crowd buy", collections.Counter(d_cr).most_common(15))
json.dump(out, open(os.path.join(HERE, "reaction.json"), "w"), indent=1)
