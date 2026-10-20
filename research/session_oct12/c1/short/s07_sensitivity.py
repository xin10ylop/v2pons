"""Sensitivity of the candidate exits (offline): (1) the trigger window (the family's trigger max_blocks, config) 60/80/100/120/150/400 with
hold 20/30/40 and tp 6% cap 40; (2) the regime without 0xbd9dc5f6's pools whose buy came after T+62 (a no-holder path inside our hold);
(3) the sell landing one block later (LAND 3) and at the end of its block; (4) per 6-h slice with max_blocks 100; (5) every pull of a triggered
pool by launch offset vs T + 2 + N + 2 (where a hold of N would land)."""
import sim
from groups import *
X = json.load(open(S("s04_exits.json"))); R = X["rows"]
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]
NONE = lambda r: r["group"] == "none" and not r["bd13"]
def m(rows, kind, e, st="0.002"):
    v = [r["res"][f"{kind} {st}"][e] for r in rows if f"{kind} {st}" in r["res"]]
    return (sum(v) / len(v), sum(1 for x in v if x <= -1), len(v)) if v else (0, 0, 0)
print("(1) trigger max_blocks x exit, T-aligned 0.002: mean gross (pulled/n)")
EX = ["hold 20", "hold 30", "hold 40", "hold 60", "tp 6% cap 40"]
print(f"  {'max_blocks':>10s} {'set':8s} " + " ".join(f"{e:>20s}" for e in EX))
for mb in (60, 80, 100, 120, 150, 400):
    for nm, pr in (("regime", REG), ("none", NONE), ("all", lambda r: True)):
        g = [r for r in R if pr(r) and r["T"] <= mb]
        print(f"  {mb:10d} {nm:8s} " + " ".join(f"{a:+7.2%} ({k}/{n})".rjust(20) for a, k, n in (m(g, 'T', e) for e in EX)))
print("\n(2) regime without the 5 bd13 pools whose 0xbd9dc5f6 buy came after T+62 (T-aligned):")
g = [r for r in R if REG(r) and not (r["bd13"] and r["group"] == "none")]
for e in ["hold 10", "hold 20", "hold 30", "hold 40", "hold 60", "tp 6% cap 45", "tp 6% cap 50"]:
    a, k, n = m(g, "T", e); a2, k2, n2 = m([r for r in g if r["T"] <= 100], "T", e)
    print(f"  {e:14s} all T: {a:+6.2%} ({k}/{n})   T <= 100: {a2:+6.2%} ({k2}/{n2})")
print("\n(3) landing: the sell's price taken one block later (LAND 3) / at the end of the landing block, regime T-aligned 0.002, all T and T <= 100:")
D = load(); byp = {p["pid"]: p for p in D["pools"]}
def resim(land, end_of_block):
    out = {}
    for r in R:
        if not REG(r): continue
        p = byp[r["pid"]]
        ob = [s for s in p["sw"] if s["cls"] == "ours" and s["buy"]]
        if ob:
            b = ob[0]; i = p["sw"].index(b); prev = p["sw"][i - 1]
            t = Trade(p, i - 1, prev["sqrtP"], prev["liq"], b["bn"], 2 * 10 ** 15, skip={s["tx"] for s in p["sw"] if s["cls"] == "ours"}, fee0=prev["fee"])
        else:
            Eb = p["lb"] + p["T"] + 2; i, sp, L, fee = entry_state(p, Eb); t = Trade(p, i, sp, L, Eb, 2 * 10 ** 15, fee0=fee)
        res = {}
        for n in (10, 20, 30, 40, 60):
            X_ = t.Eb + n + land
            res[n] = t.ret_at_landing(X_ + 1 if end_of_block else X_)[0]
        out[r["pid"]] = (r["T"], res)
    return out
for land, eob, nm in ((2, False, "LAND 2, top of block (base)"), (3, False, "LAND 3, top of block"), (2, True, "LAND 2, end of block")):
    o = resim(land, eob)
    cells = []
    for n in (10, 20, 30, 40, 60):
        v = [x[1][n] for x in o.values()]; v2 = [x[1][n] for x in o.values() if x[0] <= 100]
        cells.append(f"hold {n}: {sum(v) / len(v):+6.2%} ({sum(1 for z in v if z <= -1)}) | {sum(v2) / len(v2):+6.2%} ({sum(1 for z in v2 if z <= -1)})")
    print(f"  {nm:28s} " + "   ".join(cells))
print("\n(4) per 6-h slice, trigger max_blocks 100 (T <= 100), T-aligned 0.002: hold 30 / hold 40 / tp 6% cap 40: mean (pulled/n)")
for sn in SLICE_NAMES:
    for nm, pr in (("regime", REG), ("none", NONE)):
        g = [r for r in R if pr(r) and r["slice"] == sn and r["T"] <= 100]
        if not g: continue
        print(f"  {sn:16s} {nm:7s} " + "  ".join(f"{e}: {a:+6.2%} ({k}/{n})" for e, (a, k, n) in ((e, m(g, 'T', e)) for e in ("hold 30", "hold 40", "tp 6% cap 40"))))
print("\n(5) pulls of triggered pools within launch + 260, by launch offset (with T and the group): where a hold would have landed")
pp = sorted((p["pull"], p["T"], p["pull"] - p["T"], classify(p)[0], utc(p["ts"]), p["pid"][:10]) for p in D["pools"] if p["T"] is not None and p["pull"] is not None and p["pull"] <= 260)
for x in pp: print(f"  pull at launch+{x[0]:4d}  T {x[1]:4d}  pull at T+{x[2]:4d}  {x[3]:7s} {x[4]} {x[5]}   a hold of 30 lands at launch+{x[1] + 34}, of 40 at launch+{x[1] + 44}")
allp = sorted(p["pull"] for p in D["pools"] if p["pull"] is not None)
print(f"  all 208 pools (with and without a trigger): earliest pulls at launch+{allp[:6]}")
