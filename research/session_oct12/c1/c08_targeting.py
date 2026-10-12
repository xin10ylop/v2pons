"""Is the reaction targeted at us? (offline, c04 + c05). For every triggered pool: pull - T, the router's buying (by T+60, after T+62), the
gap from the router's last buy to the pull; our 5 filled pools and 3 reverted-buy pools against all other triggered pools (36 h and the 8 h
around our trades, Oct 11 19:00 - Oct 12 03:00 UTC): the share pulled by T+62 / T+120 / T+200 with Fisher exact p (one-sided)."""
from common import *
from math import comb
D = json.load(open(J("c05_pools.json"))); P = D["pools"]
O = json.load(open(J("c04_ours.json")))
rev = {f["c1"] for f in O if f["c1"] and f["status"] == 0 and f["input"][2:10] == "5ed06f60"}
filled = {p["pid"] for p in P if any(s["cls"] == "ours" and s["buy"] for s in p["sw"])}
TP = [p for p in P if p["T"] is not None]
import calendar
w0 = calendar.timegm((2026, 10, 11, 19, 0, 0)); w1 = calendar.timegm((2026, 10, 12, 3, 0, 0))
def fisher_greater(a, n1, b, n2):
    """P(X >= a) for X ~ hypergeometric: a of n1 'ours' pulled, b of n2 others pulled"""
    K = a + b; N = n1 + n2
    return sum(comb(K, x) * comb(N - K, n1 - x) for x in range(a, min(K, n1) + 1)) / comb(N, n1)
def row(p):
    rb = [s for s in p["sw"] if s["buy"] and s["cls"] == "router" and (p["pullpos"] is None or (s["bn"], s["li"]) < tuple(p["pullpos"]))]
    last = max((s["off"] for s in rb), default=None)
    return {"pid": p["pid"], "ts": p["ts"], "T": p["T"], "pullT": None if p["pull"] is None else p["pull"] - p["T"], "eth60": sum(s["eth"] for s in rb if s["off"] <= p["T"] + 60),
            "n_after62": sum(1 for s in rb if s["off"] > p["T"] + 62), "gap_last": None if (p["pull"] is None or last is None) else p["pull"] - last, "age": p["age"]}
R = {p["pid"]: row(p) for p in TP}
print("== our 5 filled and 3 reverted pools")
for pid in sorted(filled | rev, key=lambda x: R[x]["ts"]):
    r = R[pid]; print(f"  {utc(r['ts'])} {pid[:12]} {'FILLED ' if pid in filled else 'REVERTED'} T +{r['T']} pull T+{r['pullT']} router ETH by T+60 {r['eth60']:.3f} router buys after T+62 before the pull {r['n_after62']} last router buy -> pull {r['gap_last']}")
for nm, lo, hi in (("36 h", 0, 1 << 40), ("Oct 11 19:00 - Oct 12 03:00", w0, w1)):
    G = [R[p["pid"]] for p in TP if lo <= p["ts"] < hi and p["age"] >= p["T"] + 300]
    others = [r for r in G if r["pid"] not in filled and r["pid"] not in rev]
    ours = [r for r in G if r["pid"] in filled]; rv = [r for r in G if r["pid"] in rev]
    print(f"\n== {nm}: triggered and >= T+300 old: {len(G)} (ours filled {len(ours)}, reverted {len(rv)}, others {len(others)})")
    for X in (62, 100, 120, 200):
        k = lambda g: sum(1 for r in g if r["pullT"] is not None and r["pullT"] <= X)
        print(f"   pulled by T+{X:3d}: ours filled {k(ours)}/{len(ours)}, reverted {k(rv)}/{len(rv)}, others {k(others)}/{len(others)} ({k(others) / max(1, len(others)):.1%});"
              f" Fisher one-sided p (filled vs others) {fisher_greater(k(ours), len(ours), k(others), len(others)):.2g}")
    pt = sorted(r["pullT"] for r in others if r["pullT"] is not None)
    print(f"   others: pull - T p5/10/25/50 {[pct(pt, q) for q in (.05, .1, .25, .5)]}; the {sum(1 for x in pt if x <= 200)} pulled by T+200: "
          f"{[(utc(r['ts'])[6:], r['pullT'], round(r['eth60'], 2), r['n_after62']) for r in sorted(others, key=lambda r: r['ts']) if r['pullT'] is not None and r['pullT'] <= 200]}")
    zero = [r for r in others if r["n_after62"] == 0 and r["pullT"] is not None]
    print(f"   others where the router never bought after T+62: {len(zero)}; their pull - T p25/50/75 {[pct(sorted(r['pullT'] for r in zero), q) for q in (.25, .5, .75)]}")
# router timeline in our filled pools
print("\n== router buys around our trades (offset from our buy: ETH)")
for p in sorted([p for p in P if p["pid"] in filled], key=lambda p: p["lb"]):
    ob = next(s for s in p["sw"] if s["cls"] == "ours" and s["buy"]); osl = next((s for s in p["sw"] if s["cls"] == "ours" and not s["buy"]), None)
    rb = [(s["off"] - ob["off"], round(s["eth"], 3)) for s in p["sw"] if s["cls"] == "router" and s["off"] - ob["off"] <= 300 and s["off"] >= p["T"]]
    rs = [(s["off"] - ob["off"], round(s["eth"], 3)) for s in p["sw"] if s["cls"] == "router" and not s["buy"] and s["off"] - ob["off"] <= 300]
    print(f"  {p['pid'][:12]} our buy +{ob['off']} (T+{ob['off'] - p['T']}), sell {'buy+%d' % (osl['off'] - ob['off']) if osl else '-'}, pull buy+{p['pull'] - ob['off']}; router buys (buy-relative, ETH) {[x for x in rb if True][:12]}; router sells {rs[:5]}")
