"""The reaction study (offline, from c05_pools.json). Does the C-1 operator pull after an outside buy?
Outside = a buy whose transaction does not go to the operator's router, is not ours, not from a C-1 launch wallet and not from an EOA seen
calling the router; recurring = an outside EOA buying in >= 5 of the pools, one-off = the rest. Non-dust >= 0.001 ETH; our size 0.001-0.0105.
Measure 1: pools with an outside buy in (trigger, T+10] (our window) vs pools without: the first pull after that buy within 62/100/200 blocks,
the lag distribution, and the expected count from the control pools (no outside buy >= 0.0001 ETH in the window), matched on dt = buy - T as
in analysis V: the share of control pools still unpulled at T+dt whose first pull falls in (T+dt, T+dt+W]. Measure 2: the same for the first
outside buy after the trigger at any offset, and per buy event. Measure 4: 6-h slices. Measure 5: the rate with Wilson and exact bounds."""
from common import *
import collections
D = json.load(open(J("c05_pools.json"))); P = D["pools"]; head = D["head"]
OUT = ("recurring", "oneoff")
pos = lambda s: (s["bn"], s["li"])
CAP = 3000                                   # c03 attributed every swap up to min(pull, launch + 3000): events are taken only there
def after_T(p, s): return p["Tpos"] is not None and pos(s) > tuple(p["Tpos"]) and s["off"] <= CAP
def before_pull(p, s): return p["pullpos"] is None or pos(s) < tuple(p["pullpos"])
def lag(p, s): return None if p["pull"] is None else p["pull"] - s["off"]
TP = [p for p in P if p["T"] is not None]
print(f"pools {len(P)}, with a trigger {len(TP)}; launch span {utc(min(p['ts'] for p in P))} .. {utc(max(p['ts'] for p in P))} UTC; head {head}")
def ctrl_expected(ctrl, dt, Wn):
    alive = [c for c in ctrl if c["pull"] is None or c["pull"] > c["T"] + dt]
    alive = [c for c in alive if c["age"] >= c["T"] + dt + Wn]
    if not alive: return 0.0
    return sum(1 for c in alive if c["pull"] is not None and c["pull"] <= c["T"] + dt + Wn) / len(alive)
def study(name, sel, win, ctrl_sel, show=True):
    """sel(p, s) picks qualifying outside buys; win = max(off - T) or None; the first qualifying buy per pool is the event."""
    ev = []; ctrl = []
    for p in TP:
        q = [s for s in p["sw"] if s["buy"] and after_T(p, s) and before_pull(p, s) and sel(p, s) and (win is None or s["off"] - p["T"] <= win)]
        if q: ev.append((p, q[0]))
        elif not any(s["buy"] and after_T(p, s) and before_pull(p, s) and ctrl_sel(p, s) and (win is None or s["off"] - p["T"] <= win) for s in p["sw"]): ctrl.append(p)
    res = {"name": name, "n": len(ev), "ctrl": len(ctrl), "W": {}}
    lines = []
    for Wn in (10, 30, 62, 100, 200):
        el = [(p, s) for p, s in ev if p["age"] >= s["off"] + Wn]
        k = sum(1 for p, s in el if p["pull"] is not None and p["pull"] - s["off"] <= Wn)
        e = sum(ctrl_expected(ctrl, s["off"] - p["T"], Wn) for p, s in el)
        lo, hi = wilson(k, len(el)); res["W"][Wn] = (k, len(el), round(e, 2))
        lines.append(f"    pull within {Wn:3d} blocks of the buy: {k:3d}/{len(el):3d} = {k / max(1, len(el)):6.1%} (Wilson 95% {lo:.1%}-{hi:.1%}); expected from {len(ctrl)} controls {e:5.1f} ({e / max(1, len(el)):.1%})")
    lg = sorted(lag(p, s) for p, s in ev if lag(p, s) is not None)
    res["lags"] = lg
    if show:
        print(f"\n== {name}: {len(ev)} pools with such a buy, {len(ctrl)} control pools")
        print("\n".join(lines))
        print(f"    lag (pull - buy) p10/25/50/75/90: {[pct(lg, q) for q in (.1, .25, .5, .75, .9)]}; never pulled {sum(1 for p, s in ev if p['pull'] is None)}; lags <= 200: {[x for x in lg if x <= 200]}")
        cl = sorted(c["pull"] - c["T"] for c in ctrl if c["pull"] is not None)
        print(f"    controls: pull - T p10/25/50/75/90 {[pct(cl, q) for q in (.1, .25, .5, .75, .9)]}; pulled by T+62 {sum(1 for x in cl if x <= 62)}/{len(ctrl)}, by T+100 {sum(1 for x in cl if x <= 100)}, by T+200 {sum(1 for x in cl if x <= 200)}")
    return res, ev, ctrl
nd = lambda p, s: s["cls"] in OUT and s["eth"] >= 0.001
ours_sz = lambda p, s: s["cls"] in OUT and 0.001 <= s["eth"] <= 0.0105
anyout = lambda p, s: s["cls"] in OUT
oneoff_nd = lambda p, s: s["cls"] == "oneoff" and s["eth"] >= 0.001
rec_any = lambda p, s: s["cls"] == "recurring"
dust_ctrl = lambda p, s: s["cls"] in OUT and s["eth"] >= 0.0001
R = {}
print("\n######## MEASURE 1: an outside buy in (trigger, T+10] (our window)")
for nm, f, cs in (("non-dust (>= 0.001) outside, T..T+10", nd, dust_ctrl), ("our size (0.001-0.0105) outside, T..T+10", ours_sz, dust_ctrl),
                  ("one-off non-dust, T..T+10", oneoff_nd, dust_ctrl), ("any-size outside, T..T+10", anyout, anyout), ("recurring any size, T..T+10", rec_any, anyout)):
    R["m1|" + nm], ev, ctrl = study(nm, f, 10, cs)
    for p, s in ev:
        if s["eth"] >= 0.001:
            print(f"      {utc(p['ts'])} pool {p['pid'][:12]} T +{p['T']} buy +{s['off']} (T+{s['off'] - p['T']}) {s['eth']:.5f} ETH {s['cls']} {s['from'][:10]} nonce {s.get('nonce')} via {s['to'][:10]}:{s['sel']}:{s['n']}"
                  f" | pull {p['pull']} (lag {lag(p, s)}) | router ETH by buy+60 {sum(x['eth'] for x in p['sw'] if x['buy'] and x['cls'] == 'router' and x['off'] <= s['off'] + 60):.3f}")
    if nm.startswith("our size"): break
print("\n######## MEASURE 2: the first outside buy after the trigger at any offset (before the pull)")
for nm, f, cs in (("non-dust outside, any offset", nd, dust_ctrl), ("our size outside, any offset", ours_sz, dust_ctrl), ("one-off non-dust, any offset", oneoff_nd, dust_ctrl),
                  ("any-size outside, any offset", anyout, anyout)):
    R["m2|" + nm], ev, ctrl = study(nm, f, None, cs)
print("\n== every non-dust outside buy after T (per event, before the pull): lag to the first pull")
E = []
for p in TP:
    for s in p["sw"]:
        if s["buy"] and after_T(p, s) and before_pull(p, s) and nd(p, s): E.append((p, s))
for Wn in (10, 30, 62, 100, 200):
    el = [(p, s) for p, s in E if p["age"] >= s["off"] + Wn]; k = sum(1 for p, s in el if p["pull"] is not None and p["pull"] - s["off"] <= Wn)
    print(f"    within {Wn:3d}: {k}/{len(el)} = {k / max(1, len(el)):.1%}")
print("    by size: " + "; ".join(f"{a}-{b} ETH n {len(g)} pulled<=62 {sum(1 for p, s in g if p['pull'] is not None and p['pull'] - s['off'] <= 62)} <=200 {sum(1 for p, s in g if p['pull'] is not None and p['pull'] - s['off'] <= 200)}"
                         for a, b, g in [(a, b, [(p, s) for p, s in E if a <= s['eth'] < b]) for a, b in ((0.001, 0.0105), (0.0105, 0.1), (0.1, 100))]))
with open(J("c06_cases.txt"), "w") as f:
    for p, s in sorted(E, key=lambda x: x[0]["lb"]):
        f.write(f"{utc(p['ts'])} pool {p['pid'][:14]} T +{p['T']} buy +{s['off']} (T+{s['off'] - p['T']}) {s['eth']:.6f} {s['cls']:9s} {s['from']} nonce {s.get('nonce')} via {s['to']}:{s['sel']}:{s['n']} | pull {p['pull']} lag {lag(p, s)}\n")
print(f"    ({len(E)} events listed in c06_cases.txt)")
print("\n######## MEASURE 4: 6-h slices (by launch time): pulled inside the hold (pull <= T+62) with / without a non-dust outside buy in (T, T+10]; and pull <= buy+62 after any non-dust outside buy after T")
t0 = min(p["ts"] for p in P); hd_ts = max(p["ts"] for p in P)
import math
S = []
edges = []
tend = json.load(open(J("c01_meta.json")))["head_ts"]
e = tend
while e > t0: edges.append(e); e -= 6 * 3600
edges = sorted(edges + [e])
for a, b in zip(edges, edges[1:]):
    G = [p for p in TP if a <= p["ts"] < b and p["age"] >= p["T"] + 262]
    w = [p for p in G if any(s["buy"] and after_T(p, s) and before_pull(p, s) and nd(p, s) and s["off"] - p["T"] <= 10 for s in p["sw"])]
    wo = [p for p in G if p not in w]
    hold = lambda g: sum(1 for p in g if p["pull"] is not None and p["pull"] <= p["T"] + 62)
    ev2 = [(p, s) for p in G for s in p["sw"][:] if s["buy"] and after_T(p, s) and before_pull(p, s) and nd(p, s)]
    first = {}
    for p, s in ev2: first.setdefault(p["pid"], (p, s))
    k2 = sum(1 for p, s in first.values() if p["pull"] is not None and p["pull"] - s["off"] <= 62)
    allp = [p for p in P if a <= p["ts"] < b]
    rb = sorted(sum(s["eth"] for s in p["sw"] if s["buy"] and s["cls"] == "router" and s["off"] <= p["T"] + 60) for p in G)
    print(f"  {utc(a)}-{utc(b)[6:]}: launches {len(allp):3d}, triggered+complete {len(G):3d}; router ETH by T+60 p50 {pct(rb, .5) or 0:.3f}; pulled <= T+62: with outsider in T..T+10 {hold(w)}/{len(w)}, without {hold(wo)}/{len(wo)};"
          f" pools with a non-dust outside buy after T {len(first)}, pulled <= buy+62 {k2}")
    S.append({"from": a, "to": b, "launches": len(allp), "G": len(G), "w": (hold(w), len(w)), "wo": (hold(wo), len(wo)), "any": (k2, len(first))})
json.dump({"R": R, "S": S}, open(J("c06_reaction.json"), "w"), default=str)
