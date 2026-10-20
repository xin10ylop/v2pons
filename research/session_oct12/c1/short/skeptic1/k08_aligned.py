"""Skeptic 1: holder-aligned exits (offline). For every outside >= 0.001 ETH buy (class 'out') after the engine's T and before the pull, held
>= 30 blocks or into the pull, at h - T <= 130 (the reaction window; bd9dc5f6 buys at T+18..121): our 0.002 ETH buy right behind it (same
block, next in line), then hold N / take-profit as in k02 (our position held while the outsider holds, the reaction's clock = its buy).
Also our 5 real fills (h = our buy). Grouped by: ours, 0xbd9dc5f6 from 13:15 UTC (Skeptic 1's reaction cluster), other outsiders."""
import json, statistics as st, calendar, time
from k02_sim import *
D = load(); P = D["pools"]; HEAD = D["head"]
T1315 = calendar.timegm((2026, 10, 12, 13, 15, 0)); BD = "0xbd9dc5f684ed24f4a06559ff9dc736748cbbbc41"
class SimAfter(Sim):
    """entry right after swap index i0 (the holder's buy), at its block"""
    def __init__(self, p, i0, stake):
        sw = p["sw"]; s0 = sw[i0]
        q = dict(p); q["sw"] = [dict(x) for x in sw]
        # reuse Sim by faking the trigger: E = s0's block; pre = swaps up to i0 (same block later swaps go AFTER ours)
        self.p = p; self.stake = stake; self.real = False; self.E = s0["bn"]
        pre = sw[:i0 + 1]; post = sw[i0 + 1:]; prev = s0["sp"]; fee0 = s0["fee"]; self.L = sw[0]["liq"]
        mv = []; last = p["sqrtP0"]
        for s in sw:
            mv.append(("b", QD / Dc(s["sp"]) - QD / Dc(last)) if s["buy"] else ("s", Dc(s["sp"]) - Dc(last))); last = s["sp"]
        self.tokens = v4math.buy_out_int(prev, self.L, stake, fee0)
        x = net(stake, fee0); den = self.L + (x * prev) // Q96; sp = Dc((self.L * prev + den - 1) // den)
        self.path = [(self.E, sp, fee0)]
        for k, s in enumerate(post):
            if s["c"] == "ours": continue
            kind, d = mv[i0 + 1 + k]
            sp = QD / (QD / sp + d) if kind == "b" else sp + d
            self.path.append((s["bn"], sp, s["fee"]))
        self.post = [s for s in post if s["c"] != "ours"]
        self.pullb = p["pullpos"][0] if p["pullpos"] else None
        cs = float(p["sqrtP0"])
        for s in pre:
            if s["buy"] and s["c"] != "ours": cs = v4math.sqrt_after_buy(cs, self.L, net(s["eth_wei"], 100))
        self.copy0 = v4math.sqrt_after_buy(cs, self.L, net(stake, 100))
ev = []
for p in P:
    T = p["Teng"]
    ours = [i for i, s in enumerate(p["sw"]) if s["c"] == "ours" and s["buy"]]
    if ours:
        ev.append(("ours", p, Sim(p, p["T"], 2 * 10 ** 15), 2)); continue
    if T is None or p["sqrtP0"] != 792280926924313289846529216293289: continue
    done = set()
    for i, s in enumerate(p["sw"]):
        if s["c"] != "out" or not s["buy"] or s["eth_wei"] < 10 ** 15 or s["off"] <= T or s["off"] - T > 130 or s["from"] in done: continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        if HEAD - s["bn"] < 70: continue
        done.add(s["from"])
        sl = next((x for x in p["sw"] if not x["buy"] and x["from"] == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"])), None)
        if sl is not None and (not p["pullpos"] or (sl["bn"], sl["li"]) < tuple(p["pullpos"])) and sl["bn"] - s["bn"] < 30: continue
        g = "bd13" if (s["from"] == BD and p["ts"] >= T1315) else ("bd<13:15" if s["from"] == BD else "other")
        ev.append((g, p, SimAfter(p, i, 2 * 10 ** 15), s["off"] - T))
EXITS = [("hold", 10), ("hold", 20), ("hold", 30), ("hold", 40), ("hold", 60), ("tp", (0.04, 30)), ("tp", (0.04, 40)), ("tp", (0.06, 50))]
nm = lambda e: f"hold {e[1]}" if e[0] == "hold" else f"tp{int(e[1][0] * 100)} cap{e[1][1]}"
def r(sim, e): return sim.hold(e[1]) if e[0] == "hold" else sim.tp(*e[1])[0]
print(f"events: {len(ev)}; by group " + str({g: sum(1 for x in ev if x[0] == g) for g in ('ours', 'bd13', 'bd<13:15', 'other')}))
print(f"  {'group':10s} {'n':>3s} " + " ".join(f"{nm(e):>16s}" for e in EXITS) + "   (mean, pulled)")
for g in ("ours", "bd13", "bd<13:15", "other", "ALL"):
    sel = [x for x in ev if g == "ALL" or x[0] == g]
    cells = []
    for e in EXITS:
        v = [r(x[2], e) for x in sel]; cells.append(f"{st.mean(v):+7.2%} {sum(1 for y in v if y <= -1):2d}p")
    print(f"  {g:10s} {len(sel):3d} " + " ".join(f"{c:>16s}" for c in cells))
print("\nevents pulled within 80 blocks of the entry (group, pool, h-T, pull after entry, router buys after entry):")
for g, p, sim, hT in ev:
    if sim.pullb is not None and sim.pullb - sim.E <= 80:
        rb = [s["bn"] - sim.E for s in sim.post if s["c"] == "router" and s["buy"] and s["bn"] < sim.pullb][:8]
        print(f"  {g:9s} {p['pid'][:10]} {time.strftime('%m-%d %H:%M', time.gmtime(p['ts']))} h-T {hT:+4d} pull +{sim.pullb - sim.E:3d} router {rb} | "
              + " ".join(f"{nm(e)}:{'-100' if r(sim, e) <= -1 else format(r(sim, e), '+.1%')}" for e in EXITS))
