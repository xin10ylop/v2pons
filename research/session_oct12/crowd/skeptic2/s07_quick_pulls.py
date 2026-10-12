"""the crowd-then-quick-pull pattern: pools pulled within 40 blocks of the engine's trigger (the crowd's first real buy at or after + 2, or anyone's
ETH-value buy of >= 0.005): when, how fast, and what happened between the trigger and the pull (who bought, who sold). Our trigger-branch sell
lands at trigger + 20, so a pull within 20 of the trigger in a pool whose trigger is <= + 60 is a -100% trade. Swap senders after + 80 come from the
reaction analyst's raw rows (reaction/r04_pools_cache.jsonl), read with own code."""
from common import *
import collections
P = {p["pool"]: p for p in jl(J("s04_pools_cache.jsonl"))}
R = {}
for l in open(J("../reaction/r04_pools_cache.jsonl")):
    r = json.loads(l); R[r["pool"]] = r
rows = []
for pool, p in P.items():
    if p["trig"] is None: continue
    r = R[pool]; pull = p["pull"]["off"] if p["pull"] else r["pull_off"]
    if pull is None: continue
    rows.append((pull - p["trig"], p, r, pull))
rows.sort(key=lambda x: x[0])
def period(ts):
    d = time.strftime("%m-%d", time.gmtime(ts)); return "Oct 3-7" if d <= "10-07" else "Oct 8-9" if d <= "10-09" else "Oct 10-12"
print("pull within N blocks of the trigger, by launch period (all trigger offsets):")
for per in ("Oct 3-7", "Oct 8-9", "Oct 10-12"):
    g = [x for x in rows if period(x[1]["ts"]) == per]
    print(f"  {per:<10} pools with a trigger and a pull {len(g):>4}: within 20 {sum(1 for x in g if x[0] <= 20)}, 25 {sum(1 for x in g if x[0] <= 25)}, 30 {sum(1 for x in g if x[0] <= 30)},"
          f" 40 {sum(1 for x in g if x[0] <= 40)}; pull - trigger p10 {pct([x[0] for x in g], .1)} p50 {pct([x[0] for x in g], .5)}")
print("\ncases (pull within 30 of the trigger):")
for d, p, r, pull in rows:
    if d > 30: break
    t = p["trig"]; sw = [s for s in r["sw"] if t <= s["off"] <= pull]
    cb = sum(s["dq"] for s in sw if s["k"] in ("crowd", "crowd2", "crowd_r") and s["dq"] > 0) / 1e18
    cs = sum(-s["dq"] for s in sw if s["k"] in ("crowd", "crowd2", "crowd_r") and s["dq"] < 0) / 1e18
    ob = [(s["off"], round(s["dq"] / 1e18, 4), (s["from"] or "?")[:8]) for s in sw if s["k"] == "other" and s["dq"] > 0]
    os_ = [(s["off"], round(-s["dq"] / 1e18, 4), (s["from"] or "?")[:8]) for s in sw if s["k"] == "other" and s["dq"] < 0]
    un = sum(1 for s in sw if s["k"] == "unknown")
    pre = [(s["off"], round(s["dq"] / 1e18, 4), (s["from"] or "?")[:8]) for s in r["sw"] if s["k"] == "other" and s["dq"] > 0 and s["off"] < t]
    print(f"  {utc(p['ts'])} {p['pool'][:10]} trigger +{t} pull +{pull} (after {d}): crowd in {cb:.3f} ETH, crowd out {cs:.3f}; outside buys before the trigger {pre[:6]}"
          f"; outside buys in it {ob[:6]}; outside sells in it {os_[:6]}; unknown {un}")
