"""Skeptic 1: validate my replay (k02_sim) (1) against our 5 real fills: real tokens bought, real ETH back at the real sell's own place, and
the box-log returns (+4.1, +6.7, 0.0, +3.5, -100%); (2) against the analyst's s04_exits.json, pool by pool, for the T-aligned 0.002 ETH exits."""
import json, os
from k02_sim import *
D = load(); P = {p["pid"]: p for p in D["pools"]}
print("== (1) our 5 real fills")
for p in sorted(D["pools"], key=lambda p: p["ts"]):
    ob = [s for s in p["sw"] if s["c"] == "ours"]
    if not ob or not ob[0]["buy"]: continue
    b = ob[0]; sl = [s for s in ob if not s["buy"]]
    sim = Sim(p, p["T"], b["eth_wei"])
    line = f"  {p['pid'][:10]} T+{b['off'] - p['T']} buy {b['eth_wei'] / 1e18:.6f} ETH tokens real {b['tok']} sim {sim.tokens} (diff {sim.tokens - b['tok']:+d})"
    if sl:
        s = sl[0]
        # the state right before our real sell (by log index), sells of ours removed from the path
        st = sim.path[0]
        for q, sw in zip(sim.path[1:], sim.post):
            if (sw["bn"], sw["li"]) < (s["bn"], s["li"]): st = q
        eth_sim = v4math.sell_out_int(int(st[1]), sim.L, b["tok"], s["fee"])
        line += f" | sell at buy+{s['bn'] - b['bn']} ETH real {s['eth_wei']} sim {eth_sim} (rel {eth_sim / s['eth_wei'] - 1:+.2e}); real gross {s['eth_wei'] / b['eth_wei'] - 1:+.2%}"
    else:
        line += f" | no sell (pull at buy+{p['pullpos'][0] - b['bn']}): -100%"
    print(line)
print("\n== (2) against the analyst's s04_exits.json (T-aligned, 0.002 ETH, analyst's T)")
A = json.load(open(os.path.join(H, "..", "s04_exits.json")))
mx = {}; n = 0; worst = []
for r in A["rows"]:
    p = P.get(r["pid"])
    if p is None: print("  missing", r["pid"]); continue
    sim = Sim(p, r["T"], 2 * 10 ** 15); n += 1
    for N in (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60):
        a = r["res"]["T 0.002"][f"hold {N}"]; m = sim.hold(N); d = abs(a - m)
        mx[N] = max(mx.get(N, 0), d)
        if d > 1e-4: worst.append((d, r["pid"][:10], N, a, m))
    for tp in (0.02, 0.03, 0.04, 0.06, 0.08):
        for cap in (30, 45, 50, 60):
            a = r["res"]["T 0.002"][f"tp {int(tp * 100)}% cap {cap}"]; m = sim.tp(tp, cap)[0]; d = abs(a - m)
            mx[f"tp{tp}c{cap}"] = max(mx.get(f"tp{tp}c{cap}", 0), d)
            if d > 1e-4: worst.append((d, r["pid"][:10], f"tp{tp}c{cap}", a, m))
print(f"  pools compared {n}; max |analyst - mine| per exit:", {k: f"{v:.1e}" for k, v in mx.items()})
print("  differences > 1e-4:", len(worst))
for w in sorted(worst, reverse=True)[:15]: print("   ", w)
print("  pools whose L changes before the pull:", [p["pid"][:10] for p in D["pools"] if p["T"] is not None and Sim(p, p["T"], 2 * 10 ** 15).lchg])
