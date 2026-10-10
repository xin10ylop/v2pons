"""Adversarial review 1: fingerprint fields of every buy on the 143 launches, by class; the speck wallet; crowd buys followed by a pull within 0-6."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
print("pools", len(pools), collections.Counter(p["kind"] for p in pools), "head", head)
ex = next(x for p in pools for x in p["sw"] if x["fp"])
print("fp keys", ex["fp"])
# fingerprint field distribution for outsider buys (non-crowd, non-us, non-dust)
c = collections.Counter()
for p in pools:
    for x in p["sw"]:
        if x["a0"] < 0 and x["cls"] == "outsider":
            f = x["fp"] or {}
            c[(f.get("type"), f.get("prio"), f.get("gas"), f.get("len"), f.get("dl_max"), (x["to"] or "")[:10], "real" if -x["a0"] >= REAL else "small")] += 1
print("outsider buy fingerprints (type, prio, gas, len, dl_max, to, size):")
for k, v in c.most_common(40): print("  ", v, k)
# how many outsider buys match each individual part of the fingerprint
parts = collections.Counter()
n = 0
for p in pools:
    for x in p["sw"]:
        if x["a0"] < 0 and x["cls"] in ("outsider", "dust"):
            f = x["fp"] or {}; n += 1
            parts["prio=0.02gwei"] += f.get("prio") == 20_000_000
            parts["len=1124"] += f.get("len") == 1124
            parts["dl_max"] += f.get("dl_max") is True
            parts["gas in set"] += f.get("gas") in (220_000, 880_000, 260_000)
            parts["to=UR"] += (x["to"] or "").startswith("0x88767899")
print("outsider+dust buys", n, dict(parts))
# speck wallet
SPECK = next(w for w in cw if w.startswith("0xb4d43149"))
sz = sorted(-x["a0"] / 1e18 for p in pools for x in p["sw"] if x["from"] == SPECK and x["a0"] < 0)
print("speck buys", len(sz), "min", sz[0], "max", sz[-1], ">=0.0002:", sum(1 for s in sz if s >= 2e-4), ">=0.0001:", sum(1 for s in sz if s >= 1e-4))
# is the speck ever the first buy >= 0.0002 after arm (+6) on an original launch (i.e. an engine trigger)?
for p in pools:
    if p["kind"] != "orig": continue
    rb = [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and x["cls"] != "us"]
    t = next((x for x in rb if 6 <= x["bn"] - p["b0"] <= 150), None)
    if t and t["from"] == SPECK: print("  speck is the trigger on", p["pid"][:10], utc(p["ts"]))
# crowd real buys followed by the pull within 0..6 blocks, on launches with no non-crowd real buy within 60 before the pull
print("crowd real buys with the pull 0..6 blocks after them (any launch):")
for p in pools:
    if not p["pull"]: continue
    pb = p["pull"]["bn"]
    for x in p["sw"]:
        if x["cls"] == "crowd" and x["a0"] <= -REAL and before_pull(p, x) and 0 <= pb - x["bn"] <= 6:
            nc = [(y["cls"], round(-y["a0"]/1e18, 6), pb - y["bn"]) for y in p["sw"] if y["a0"] < 0 and y["cls"] not in ("crowd",) and 0 <= pb - y["bn"] <= 60]
            print(f"   {utc(p['ts'])} {p['kind']} {p['pid'][:10]} {x['from'][:10]} nonce {x['nonce']} {-x['a0']/1e18:.4f} off +{x['bn']-p['b0']} lag {pb - x['bn']} | non-crowd in 60 before pull: {nc}")
