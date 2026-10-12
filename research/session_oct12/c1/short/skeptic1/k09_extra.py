"""Skeptic 1, extras (offline): (1) what a DRY test of the candidate exits would show: the no-holder path (pools with no outside >= 0.001 ETH
buy from the launch to T+62, engine T), where the engine's dry position is not in the pool and nobody reacts; (2) how often a triggered pool
already has an outside >= 0.001 ETH holder at T (the 0xcf1d880b / 0x91620507 case) and what happened to those pools; (3) the candidate exits
with the trigger window max_blocks 100 (config only)."""
import json, statistics as st
from k02_sim import *
D = load(); P = D["pools"]; HEAD = D["head"]
R = json.load(open(os.path.join(H, "k04_regime.json"))); REG = {r["pid"] for r in R}
SQ, LQ = 792280926924313289846529216293289, 100000088127620690885293
base = [p for p in P if p["Teng"] is not None and p["sqrtP0"] == SQ and p["sw"][0]["liq"] == LQ and (p["pull"] is None or p["pull"] > p["Teng"] + 2)
        and HEAD - p["lb"] >= p["Teng"] + 70]
def out_buys(p, a, b): return [s for s in p["sw"] if s["c"] == "out" and s["buy"] and s["eth_wei"] >= 10 ** 15 and a <= s["off"] <= b]
none = [p for p in base if p["pid"] not in REG and not out_buys(p, 0, p["Teng"] + 62)]
EX = [("hold", 10), ("hold", 30), ("hold", 40), ("hold", 60), ("tp", (0.04, 30)), ("tp", (0.04, 40)), ("tp", (0.06, 50))]
nm = lambda e: f"hold {e[1]}" if e[0] == "hold" else f"tp{int(e[1][0] * 100)} cap{e[1][1]}"
def r(s, e): return s.hold(e[1]) if e[0] == "hold" else s.tp(*e[1])[0]
print(f"== (1) the no-holder path (what a dry run measures): n {len(none)}")
sims = {p["pid"]: Sim(p, p["Teng"], 2 * 10 ** 15) for p in none}
for e in EX:
    v = [r(sims[p["pid"]], e) for p in none]
    print(f"  {nm(e):12s} mean {st.mean(v):+6.2%} median {st.median(v):+6.2%} up(>+0.5%) {sum(1 for x in v if x > .005):3d} under +2% {sum(1 for x in v if x < .02):3d} pulled {sum(1 for x in v if x <= -1)}")
print("\n== (2) triggered pools with an outside >= 0.001 ETH holder already at T (bought before T, not sold by T)")
pre = []
for p in base + [q for q in P if q["pid"] in REG and q not in base]:
    T = p["Teng"] if p["Teng"] is not None else p["T"]
    for s in out_buys(p, 0, T - 1):
        sl = next((x for x in p["sw"] if not x["buy"] and x["from"] == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"])), None)
        if sl is None or sl["off"] > T:
            pre.append((p["pid"][:10], s["from"][:10], round(s["eth_wei"] / 1e18, 5), s["off"] - T, None if sl is None else sl["off"] - T, T, p["pull"] - T if p["pull"] else None)); break
print(f"  {len(pre)} of {len(base)} triggered pools:")
for x in pre: print(f"   {x[0]} holder {x[1]} {x[2]} ETH at T{x[3]:+d}, sold {'never' if x[4] is None else f'T+{x[4]}'}; T launch+{x[5]}, pull T+{x[6]}")
print("\n== (3) candidate exits with max_blocks 100 (engine T <= 100)")
for name, ids in (("regime (ours + outsider at T+2..10)", [p for p in P if p["pid"] in REG]), ("no holder", none)):
    g = [p for p in ids if (p["Teng"] if p["Teng"] is not None else p["T"]) <= 100]
    ss = [Sim(p, p["Teng"] if p["Teng"] is not None else p["T"], 2 * 10 ** 15) for p in g]
    print(f"  {name}: n {len(g)} " + "  ".join(f"{nm(e)} {st.mean([r(s, e) for s in ss]):+.2%}/{sum(1 for s in ss if r(s, e) <= -1)}p" for e in EX))
    g2 = [p for p in ids if (p["Teng"] if p["Teng"] is not None else p["T"]) > 100]
    ss = [Sim(p, p["Teng"] if p["Teng"] is not None else p["T"], 2 * 10 ** 15) for p in g2]
    if ss: print(f"  {name} T > 100: n {len(g2)} " + "  ".join(f"{nm(e)} {st.mean([r(s, e) for s in ss]):+.2%}/{sum(1 for s in ss if r(s, e) <= -1)}p" for e in EX))
