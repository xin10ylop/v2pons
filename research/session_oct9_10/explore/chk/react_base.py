"""v2.433: outsider buys (not the volume bot, not the deployer) by wallet; pull within 1..15 blocks after the buy vs the base rate of a pull
in the same 15-block window among pools alive at that offset."""
import json, pickle, collections, numpy as np
R = json.load(open("../vbot/react/react.json"))
P = pickle.load(open("pools.pkl", "rb"))
fam = [p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p]
pull = {}
for p in fam:
    neg = [m for m in p["mls"] if m[4] < 0]; pull[p["pid"]] = (neg[0][0] - p["b0"]) if neg else None
def base(r, w=15):
    alive = [q for q, v in pull.items() if v is None or v > r]
    hit = [q for q in alive if pull[q] is not None and pull[q] <= r + w]
    return len(hit) / len(alive), len(alive)
v = [x for x in R if x["fam"] == "v2.433"]
byw = collections.defaultdict(list)
for x in v: byw[x["wallet"]].append(x)
print(f"{'wallet':12s} {'n':>4s} {'eth p50':>9s} {'rel p50':>7s}  pulled<=15 after  (expected at base rate)")
rows = []
for w, xs in sorted(byw.items(), key=lambda kv: -len(kv[1])):
    # one per pool: the wallet's first buy in the pool
    seenp = {}
    for x in sorted(xs, key=lambda x: x["rel"]): seenp.setdefault(x["pid"], x)
    xs1 = list(seenp.values())
    hit = sum(1 for x in xs1 if x["lag"] is not None and 0 <= x["lag"] <= 15)
    exp = sum(base(x["rel"])[0] for x in xs1)
    rows.append((w, len(xs1), np.median([x["eth"] for x in xs1]), np.median([x["rel"] for x in xs1]), hit, exp))
    print(f"{w[:12]:12s} {len(xs1):4d} {np.median([x['eth'] for x in xs1]):9.6f} {np.median([x['rel'] for x in xs1]):7.0f}  {hit:4d}  ({exp:6.1f})  lags {sorted(x['lag'] for x in xs1 if x['lag'] is not None and x['lag'] <= 15)[:12]}")
print("base rate of a pull within 15 blocks, pools alive at +3:", base(3), " at +8:", base(8), " at +45:", base(45), " at +100:", base(100))
