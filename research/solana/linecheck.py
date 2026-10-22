#!/usr/bin/env python3
"""linecheck.py trades.json: per candidate line (creator or funder), each pool's replay: reserves from the vault changes (the creation's
deposit included), buys and sells by the creator, the line's fleet (payers on 2+ pools of the line) and outsiders; the pull (the SOL vault
emptied); the reaction (the pull's delay after an outsider's buy); the price before the pull; an early seat bought in the first slot after the
creation and sold at a fixed minute (or lost when the pull came first)."""
import json, sys, collections, statistics as st
d = json.load(open(sys.argv[1]))
lines = collections.defaultdict(list)
for p in d:
    key = "creator " + p["creator"][:8] if p["creator"].startswith(("6RsDQGpH", "aPTS9Ki2")) else ("funder " + p["funder"][:8] if p.get("funder") else "creator " + p["creator"][:8])
    lines[key].append(p)
FEE = 0.0025
for key, ps in sorted(lines.items(), key=lambda kv: -len(kv[1])):
    payer_pools = collections.defaultdict(set)
    for p in ps:
        for r in p["rows"]:
            if r["sol_d"] > 0 and r["payer"] != p["creator"]: payer_pools[r["payer"]].add(p["pool"])
    fleet = {w for w, s in payer_pools.items() if len(s) >= 2}
    print(f"\n== {key}: {len(ps)} pools, SOL in {sorted(set(round(p['sol0'], 2) for p in ps))}, fleet {len(fleet)} wallets")
    react, seats = [], collections.defaultdict(list)
    for p in sorted(ps, key=lambda p: p["t"]):
        e = t = 0.0; path = []; pull = None; ev = []
        for r in p["rows"]:
            if r["err"]: continue
            e += r["sol_d"]; t += r["tok_d"]
            if r["sig"] and abs(r["sol_d"] - p["sol0"]) < 1e-6 and r["sol_d"] > 0 and not path: path.append((r["t"], e, t)); continue
            who = "creator" if r["payer"] == p["creator"] else "fleet" if r["payer"] in fleet else "outsider"
            if r["sol_d"] < 0 and e < 0.05 * p["sol0"] and pull is None: pull = r["t"]; ev.append((r["t"] - p["t"], "PULL", who, round(r["sol_d"], 3))); path.append((r["t"], e, t)); continue
            if r["sol_d"] != 0: ev.append((r["t"] - p["t"], "buy" if r["sol_d"] > 0 else "sell", who, round(r["sol_d"], 3)))
            path.append((r["t"], e, t))
        if not path or path[0][2] <= 0: continue
        p0 = path[0][1] / path[0][2]
        price_at = lambda ts: next(((ee / tt) / p0 for (tt_, ee, tt) in reversed(path) if tt_ <= ts and tt > 0 and ee > 0.05 * p["sol0"]), None)
        outs = [x for x in ev if x[1] == "buy" and x[2] == "outsider"]
        if pull and outs: react.append(min(pull - p["t"] - o[0] for o in outs if o[0] <= pull - p["t"]) if any(o[0] <= pull - p["t"] for o in outs) else None)
        before_pull = price_at(pull - 1) if pull else None
        for m in (2, 5, 10, 20):
            X = p["t"] + m * 60
            if pull and pull <= X: seats[m].append(-1.0)
            else:
                px = price_at(X); seats[m].append(px * (1 - FEE) ** 2 - 1 if px else 0.0)
        print(f"  {p['pool'][:8]} pull at {((pull - p['t']) / 60) if pull else float('nan'):5.1f} min | price before pull x{before_pull if before_pull else float('nan'):.2f} | "
              f"buys: creator {sum(1 for x in ev if x[1] == 'buy' and x[2] == 'creator')}, fleet {sum(1 for x in ev if x[1] == 'buy' and x[2] == 'fleet')}, "
              f"outsiders {len(outs)} ({sum(x[3] for x in outs):.2f} SOL) | first events {[(round(x[0]), x[1], x[2], x[3]) for x in ev[:5]]}")
    r = [x for x in react if x is not None]
    print(f"  reaction: pools with an outsider buy before the pull {len(r)}, the pull's delay after the last such buy (s): {sorted(r)[:12]}")
    for m, v in seats.items():
        print(f"  seat in at the creation, out at {m:2d} min: mean {100 * st.mean(v):+.1f}% median {100 * st.median(v):+.1f}% won {sum(x > 0 for x in v)}/{len(v)} pulled {sum(x == -1 for x in v)}")
