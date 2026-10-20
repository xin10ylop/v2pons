"""Skeptic 1: does the router stop faster than a short exit? (offline, k01_pools.json, k04_regime.json)
(1) T-aligned: the router's buying in (E, E+N] (E = engine T + 2) for the regime pools (an outsider holding at T+2..T+10, and ours) vs the
    pools with no outside buy >= 0.001 ETH from the launch to T+62 ('none'), and vs our 3 reverted-buy pools (the engine fired, no position):
    share of pools with any router buy, mean / median router ETH, and the first router buy after E.
(2) Holder-aligned, every outside non-dust (>= 0.001 ETH) buy after T that is still held 30 blocks later, any offset (h): router ETH in
    (h, h+N] against the same pool-age window (T-relative) in 'none' pools (matched on h - T within +-10 blocks), and the lag from h to the
    router's last buy before the pull and to the pull.
(3) The pull's offset from the launch for every triggered pool, by group (the age-tied pull)."""
import json, os, collections, statistics as st, random, time
from k02_sim import *
D = load(); P = D["pools"]; HEAD = D["head"]
R = json.load(open(os.path.join(H, "k04_regime.json"))); REG = {r["pid"] for r in R}
REV = {"0x3586911526", "0xd4654e14b3", "0x266d00f154"}   # our reverted buys (C1R): the engine fired, no position
SQ, LQ = 792280926924313289846529216293289, 100000088127620690885293
def any_out(p, a, b):
    return any(s["c"] == "out" and s["buy"] and s["eth_wei"] >= 10 ** 15 and a <= s["off"] <= b for s in p["sw"])
def rbuys(p, b0, b1):
    """router buys in blocks (b0, b1], before the pull"""
    return [s for s in p["sw"] if s["c"] == "router" and s["buy"] and b0 < s["bn"] <= b1 and (p["pullpos"] is None or (s["bn"], s["li"]) < tuple(p["pullpos"]))]
base = [p for p in P if p["Teng"] is not None and p["sqrtP0"] == SQ and p["sw"][0]["liq"] == LQ and (p["pull"] is None or p["pull"] > p["Teng"] + 2)
        and HEAD - p["lb"] >= p["Teng"] + 70]
none = [p for p in base if p["pid"] not in REG and not any_out(p, 0, p["Teng"] + 62)]
rev = [p for p in P if p["pid"][:12] in REV]
groups = [("regime (ours + outsider at T+2..T+10)", [p for p in P if p["pid"] in REG]),
          ("  ours only", [p for p in P if p["pid"] in REG and any(s["c"] == "ours" for s in p["sw"])]),
          ("  outsiders only", [p for p in P if p["pid"] in REG and not any(s["c"] == "ours" for s in p["sw"])]),
          ("our 3 reverted buys (fired, no position)", rev),
          ("none (no outside buy >= 0.001 to T+62)", none)]
print("== (1) T-aligned: router buying after our entry E = T+2 (before the pull)")
NS = (5, 10, 15, 20, 30, 45, 60)
for name, g in groups:
    print(f"\n  {name}: n {len(g)}")
    for N in NS:
        v = []; anyb = 0
        for p in g:
            T = p["Teng"] if p["Teng"] is not None else p["T"]
            E = p["lb"] + T + 2
            ob = [s for s in p["sw"] if s["c"] == "ours" and s["buy"]]
            if ob: E = ob[0]["bn"]
            b = rbuys(p, E, E + N); v.append(sum(s["eth_wei"] for s in b) / 1e18); anyb += bool(b)
        print(f"    (E, E+{N:2d}]: pools with a router buy {anyb:3d}/{len(g):<3d} ({anyb / len(g):5.1%})  router ETH mean {st.mean(v):.3f} median {st.median(v):.3f}")
    fb = []
    for p in g:
        T = p["Teng"] if p["Teng"] is not None else p["T"]; E = p["lb"] + T + 2
        ob = [s for s in p["sw"] if s["c"] == "ours" and s["buy"]]
        if ob: E = ob[0]["bn"]
        b = rbuys(p, E, E + 200); fb.append(b[0]["bn"] - E if b else None)
    fv = sorted(x for x in fb if x is not None)
    print(f"    first router buy after E (blocks): none within 200 in {sum(x is None for x in fb)}; p25/50/75 {[fv[int(q * (len(fv) - 1))] for q in (.25, .5, .75)] if fv else '-'}")
    if len(g) <= 12: print(f"    per pool: {fb}")

print("\n== (2) holder-aligned: every outside >= 0.001 ETH buy after T, held >= 30 blocks (any offset), before the pull")
ev = []
for p in base:
    T = p["Teng"]; done = set()
    for s in p["sw"]:
        if s["c"] != "out" or not s["buy"] or s["eth_wei"] < 10 ** 15 or s["off"] <= T or s["from"] in done: continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        if s["off"] > T + 600: continue
        done.add(s["from"])
        sl = next((x for x in p["sw"] if not x["buy"] and x["from"] == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"])), None)
        if sl is not None and sl["bn"] - s["bn"] < 30: continue
        ev.append((p, s, T))
print(f"  holder events {len(ev)} in {len({p['pid'] for p, s, T in ev})} pools; their offset h-T p10/50/90:",
      [sorted(s["off"] - T for p, s, T in ev)[int(q * (len(ev) - 1))] for q in (.1, .5, .9)])
def ctrl_eth(off_rel, N):
    v = []
    for q in none:
        a = q["lb"] + q["Teng"] + off_rel
        if q["pull"] is not None and q["lb"] + q["pull"] <= a: continue
        v.append(sum(s["eth_wei"] for s in rbuys(q, a, a + N)) / 1e18)
    return v
print(f"  {'N':>3s} {'holder: any router buy':>24s} {'ETH mean/median':>18s} | {'matched none pools: any buy':>28s} {'ETH mean/median':>18s}")
for N in (5, 10, 15, 20, 30, 45, 60):
    hv = [sum(x["eth_wei"] for x in rbuys(p, s["bn"], s["bn"] + N)) / 1e18 for p, s, T in ev]
    cv = []; cany = []
    for p, s, T in ev:
        c = ctrl_eth(s["off"] - T, N)
        if c: cv.append(st.mean(c)); cany.append(sum(1 for x in c if x > 0) / len(c))
    print(f"  {N:3d} {sum(1 for x in hv if x > 0):12d}/{len(hv):<3d} ({sum(1 for x in hv if x > 0) / len(hv):5.1%}) {st.mean(hv):8.3f}/{st.median(hv):.3f} |"
          f" {st.mean(cany):27.1%} {st.mean(cv):11.3f}")
# lags from the holder's buy
lag_last, lag_pull, lag_first = [], [], []
for p, s, T in ev:
    b = rbuys(p, s["bn"], s["bn"] + 600)
    if p["pullpos"] and p["pullpos"][0] - s["bn"] <= 600:
        lag_pull.append(p["pullpos"][0] - s["bn"]); lag_last.append((b[-1]["bn"] - s["bn"]) if b else 0)
    lag_first.append(b[0]["bn"] - s["bn"] if b else None)
fs = sorted(x for x in lag_first if x is not None)
print(f"  holder's buy -> first router buy after it: none within 600 in {sum(x is None for x in lag_first)}/{len(lag_first)}; p10/25/50 {[fs[int(q * (len(fs) - 1))] for q in (.1, .25, .5)]}")
print(f"  pulled within 600 of the holder's buy: {len(lag_pull)}; holder -> router's last buy p0/10/50 {sorted(lag_last)[:5]} median {st.median(lag_last) if lag_last else '-'};"
      f" holder -> pull smallest {sorted(lag_pull)[:8]} median {st.median(lag_pull) if lag_pull else '-'}")

print("\n== (3) pull offset from the launch, triggered pools (engine T), by group")
for name, g in (("regime", [p for p in base if p["pid"] in REG] + [p for p in P if p["pid"] in REG and p not in base]), ("none", none),
                ("all triggered", base)):
    v = sorted(p["pull"] for p in g if p["pull"] is not None)
    print(f"  {name:14s} n {len(g)} pulled {len(v)}; smallest pull offsets {v[:10]}")
early = sorted((p["pull"], p["Teng"], p["pull"] - p["Teng"], p["pid"][:10]) for p in base if p["pull"] is not None and p["pull"] - p["Teng"] <= 120)
print("  triggered pools pulled within T+120 (pull, T, pull-T):", early)
nt = sorted(p["pull"] for p in P if p["Teng"] is None and p["pull"] is not None and p["sqrtP0"] == SQ)
print("  pools with no engine trigger, smallest pull offsets:", nt[:12])
