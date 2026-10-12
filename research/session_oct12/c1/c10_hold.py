"""What the hold earns (offline, c05): the rule's gross return per pool (enter at the price after the router's first buy, as c1_recent.py; exit
at the last swap <= T+62; -100% if pulled by T+62) and the router's buying inside the hold (T+2, T+62]: our filled pools against the others,
36 h, our 8 h, and 6-h slices; plus the confidence bounds used in the report."""
from common import *
D = json.load(open(J("c05_pools.json"))); P = D["pools"]
TP = [p for p in P if p["T"] is not None and p["age"] >= p["T"] + 300]
filled = {p["pid"] for p in P if any(s["cls"] == "ours" and s["buy"] for s in p["sw"])}
import calendar
def ret(p):
    if p["pull"] is not None and p["pull"] <= p["T"] + 62: return -1.0
    inwin = [s for s in p["sw"] if s["off"] <= p["T"] + 62]
    return (p["T_sqrtP"] / inwin[-1]["sqrtP"]) ** 2 - 1
def hold_eth(p, a=2, b=62):
    return sum(s["eth"] for s in p["sw"] if s["buy"] and s["cls"] == "router" and p["T"] + a < s["off"] <= p["T"] + b and (p["pull"] is None or s["off"] < p["pull"]))
def summ(g):
    r = sorted(ret(p) for p in g); h = sorted(hold_eth(p) for p in g)
    if not r: return "n 0"
    return f"n {len(r):3d} mean {sum(r) / len(r):+.1%} median {pct(r, .5):+.1%} up {sum(1 for x in r if x > 0.003)} pulled<=T+62 {sum(1 for x in r if x == -1)}; router ETH in (T+2, T+62] mean {sum(h) / len(h):.3f} median {pct(h, .5):.3f} zero {sum(1 for x in h if x == 0)}"
w0 = calendar.timegm((2026, 10, 11, 19, 0, 0)); w1 = calendar.timegm((2026, 10, 12, 3, 0, 0))
print("our filled pools (gross from the trigger price; the box log: +4.0, +6.7, -0.0, +3.5, -100%):")
for p in sorted([p for p in TP if p["pid"] in filled], key=lambda p: p["ts"]): print(f"   {utc(p['ts'])} {p['pid'][:12]} gross {ret(p):+.1%} router ETH in hold {hold_eth(p):.3f}")
print("ours        ", summ([p for p in TP if p["pid"] in filled]))
print("others 36 h ", summ([p for p in TP if p["pid"] not in filled]))
print("others 19-03", summ([p for p in TP if p["pid"] not in filled and w0 <= p["ts"] < w1]))
M = json.load(open(J("c01_meta.json"))); e = M["head_ts"]
for k in range(6, 0, -1):
    a, b = e - 6 * 3600 * k, e - 6 * 3600 * (k - 1)
    print(f"slice {utc(a)}-{utc(b)[6:]}", summ([p for p in TP if a <= p["ts"] < b and p["pid"] not in filled]))
a = e - 3 * 3600; print(f"last 3 h      ", summ([p for p in TP if a <= p["ts"] and p["pid"] not in filled]))
pt = sorted(p["pull"] - p["T"] for p in TP if p["ts"] >= e - 6 * 3600 and p["pull"] is not None)
print(f"last 6 h: pull - T p5/10/25/50/75/90 {[pct(pt, q) for q in (.05, .1, .25, .5, .75, .9)]} (n {len(pt)})")
print("\nconfidence bounds (Wilson 95% two-sided; exact one-sided 95% upper):")
for nm, k, n in (("our relay, pulled inside the hold", 1, 5), ("our relay, pulled within 120 of our buy", 4, 5), ("strangers >= 0.001 in T+1..T+10, inside 62", 0, 3),
                 ("strangers >= 0.001 in T..T+100, held, inside 62", 0, 15), ("strangers >= 0.001 in T..T+100, all, inside 62", 0, 18),
                 ("strangers 0.001-0.0105 any offset (first per pool), inside 62", 0, 86), ("others pulled by T+62 (36 h)", 1, 161)):
    lo, hi = wilson(k, n); print(f"   {nm:62s} {k}/{n} = {k / n:.1%}  Wilson {lo:.1%}-{hi:.1%}  exact upper {cp_upper(k, n):.1%}")
be = lambda w, L=1.0: w / (w + L)
print(f"\nbreak-even pull rate at $5: winner +11% -> {be(0.11):.1%}; winner +3.5% (our 4 non-pulled fills) -> {be(0.035):.1%}; winner +7% -> {be(0.07):.1%}")
