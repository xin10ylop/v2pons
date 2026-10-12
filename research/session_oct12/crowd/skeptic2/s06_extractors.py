"""does the operator treat a known extractor differently? Within-wallet test (each wallet its own control): for every outside wallet (not the
+ 1 bot) with >= 6 pools, its pools before vs after it first sold into a crowd wave at a profit; outcomes: pulled by + 100 / + 150 and crowd's
first real buy by + 78, each against time-matched holder pools (same 12 h, a non-bot holder at the wallet's entry offset) for the drift.
Sells after + 80 need their senders: this uses the reaction analyst's raw swap rows (reaction/r04_pools_cache.jsonl: every non-crowd sell to the
pull was fetched there) with own code."""
from common import *
import collections
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"; MIN = 5 * 10 ** 14; REAL = 5 * 10 ** 15
CROWD = {"crowd", "crowd2", "crowd_r"}
P = []
for l in open(J("../reaction/r04_pools_cache.jsonl")):
    r = json.loads(l); sw = r["sw"]
    frb = next((s["off"] for s in sw if s["k"] in CROWD and s["dq"] >= REAL), None)
    W = collections.defaultdict(lambda: {"in": 0, "out": 0, "tin": 0, "tout": 0, "first": None, "sold_wave": False})
    for s in sw:
        if s["k"] != "other" or not s["from"] or s["from"] == BOT1: continue
        w = W[s["from"]]
        if s["dq"] > 0:
            w["in"] += s["dq"]; w["tin"] += -s["dt"]
            if w["first"] is None and s["dq"] >= MIN: w["first"] = s["off"]
        else:
            w["out"] += -s["dq"]; w["tout"] += s["dt"]
            if frb is not None and frb <= s["off"] <= frb + 60: w["sold_wave"] = True
    P.append({"pool": r["pool"], "ts": r["ts"], "pull": r["pull_off"], "frb": frb, "W": {k: v for k, v in W.items() if v["first"] is not None}})
P.sort(key=lambda p: p["ts"])
byw = collections.defaultdict(list)
for p in P:
    for w, v in p["W"].items():
        prof = v["sold_wave"] and v["tin"] > 0 and v["out"] * min(1, v["tin"] / max(v["tout"], 1)) > v["in"]
        byw[w].append((p, v, prof))
def ctrl(p, off):
    g = [q for q in P if abs(q["ts"] - p["ts"]) <= 6 * 3600 and q is not p and any(v["first"] <= off for v in q["W"].values()) and (q["pull"] is None or q["pull"] > off) and (q["frb"] is None or q["frb"] > off)]
    if not g: return None
    return (sum(1 for q in g if q["pull"] is not None and q["pull"] <= 100) / len(g), sum(1 for q in g if q["pull"] is not None and q["pull"] <= 150) / len(g),
            sum(1 for q in g if q["frb"] is not None and q["frb"] <= 78) / len(g))
agg = {"before": [0, 0, 0, 0, 0.0, 0.0, 0.0], "after": [0, 0, 0, 0, 0.0, 0.0, 0.0]}
nw = 0
for w, rows in byw.items():
    if len(rows) < 6: continue
    i0 = next((i for i, r in enumerate(rows) if r[2]), None)
    if i0 is None or i0 == len(rows) - 1: continue
    nw += 1
    for lab, part in (("before", rows[:i0 + 1]), ("after", rows[i0 + 1:])):
        for p, v, prof in part:
            if (p["pull"] is not None and p["pull"] <= v["first"]) or (p["frb"] is not None and p["frb"] <= v["first"]): continue
            c = ctrl(p, v["first"])
            if c is None: continue
            a = agg[lab]; a[0] += 1
            a[1] += p["pull"] is not None and p["pull"] <= 100; a[2] += p["pull"] is not None and p["pull"] <= 150; a[3] += p["frb"] is not None and p["frb"] <= 78
            a[4] += c[0]; a[5] += c[1]; a[6] += c[2]
print(f"wallets with >= 6 pools and a profitable wave sale before their last pool: {nw}")
for lab in ("before", "after"):
    a = agg[lab]
    print(f"  {lab:<6} (pools up to and incl. the first profitable sale / after it): n {a[0]}; pulled by +100 {a[1]} (expected {a[4]:.1f}, O/E {a[1]/max(a[4],1e-9):.2f});"
          f" by +150 {a[2]} (exp {a[5]:.1f}, O/E {a[2]/max(a[5],1e-9):.2f}); crowd by +78 {a[3]} (exp {a[6]:.1f}, O/E {a[3]/max(a[6],1e-9):.2f})")
