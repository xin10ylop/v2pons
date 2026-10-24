#!/usr/bin/env python3
"""linereport.py LINESCAN.json [MIN_POOLS]: linescan.py's result as a ranked markdown table, then each pre-fleet outsider case.

Rank: the verdict (OPEN, UNKNOWN, CLOSED, NO PUMP), then the paper seat's P&L at 1 SOL. Seat: bought at open_time, sold in the slot after
the operator's last buy before the pull ('seat'; an oracle exit) or after its first buy following our entry ('first', knowable live);
-100% when the pull came first. Evidence: pre-fleet cases where a verified outsider held >= 0.1 SOL into the fleet's first buy and the
fleet still came with the pull at its usual time ('for'), weaker tolerated cases ('weak': under 0.1 SOL or sold before the fleet), and
cases where the fleet skipped the pool or the pull came early ('against')."""
import json, sys, time

res = json.load(open(sys.argv[1])); min_pools = int(sys.argv[2]) if len(sys.argv) > 2 else 0
day = lambda t: time.strftime("%Y-%m-%d", time.gmtime(t))
order = {"OPEN": 0, "UNKNOWN": 1, "CLOSED": 2, "NO PUMP": 3, "NO DATA": 4}
res = [r for r in res if r["n_scanned"] >= min_pools]
res.sort(key=lambda r: (order[r["verdict"]], -(r["seat"]["seat"]["1.0"] or 0)))
f = lambda x, d=2: "-" if x is None else f"{x:.{d}f}"
print("| # | line | pools (pulled) | /day | pool SOL | pump x (range) | fleet: wallets, pools, buys at +s | pull min (median) | pre-fleet for/weak/against "
      "(max held SOL) [reduced fleet; skips: inconclusive, base rate] | verdict | seat 0.5 / 1 / 2 SOL (won, lost to pull) | first-buy exit 1 SOL | active | notes |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
same = {}
for r in res:                                      # lines that are the same pools (a funder line and its one creator)
    same.setdefault(tuple(sorted(o["pool"] for o in r["pools"])), []).append(r["id"])
def notes(r):
    out = []
    fees = [x for x in r["fees"] if abs(x - 0.0025) > 1e-9]
    if fees:
        sp = r["seat_fee_pool"]
        out.append(f"pool fee {'/'.join(f'{100 * x:g}%' for x in r['fees'])}: seat at the pool's fee {sp['0.5']:+.2f} / {sp['1.0']:+.2f} / {sp['2.0']:+.2f}")
    if r["kind"] == "hubsol":
        out.append("creators funded from exchanges: fleet identity unverified (repeat buyers could be victims)")
    if r["kind"] == "chain":
        out.append("29giReft operator: DrMHe2D7 then 29giReft")
    others = [x for x in same.get(tuple(sorted(o["pool"] for o in r["pools"])), []) if x != r["id"]]
    if others:
        out.append(f"same pools as {others[0][:8]}")
    return "; ".join(out)


for n, r in enumerate(res, 1):
    e = r["evidence"]; s = r["seat"]["seat"]; sizes = r["sol_sizes"]
    sol = f"{sizes[0]}" if len(sizes) == 1 else f"{sizes[0]}-{sizes[-1]} ({len(sizes)} sizes)"
    print(f"| {n} | `{r['id']}` ({r['kind']}) | {r['n_scanned']} ({r['pulled']}) | {r['per_day']:.1f} | {sol} | "
          f"{f(r['pump_median'])} ({f(r['pump_range'][0])}-{f(r['pump_range'][1])}) | {len(r['fleet'])}, {r['pools_with_op_buys']}, "
          f"+{f(r['first_op_s_median'], 0)}..+{f(r['last_op_s_median'], 0)} | {f(r['pull_min_range'][0], 0)}-{f(r['pull_min_range'][1], 0)} "
          f"({f(r['pull_min_median'], 0)}) | {e['for_held']}/{e['for_weak']}/{e['against']} ({f(e['max_held_sol'])}) [{e.get('fleet_reduced', 0)}; {e['skip_inconclusive']}, "
          f"{f(e['base_skip'])}] | {r['verdict']} | "
          f"{s['0.5']:+.2f} / {s['1.0']:+.2f} / {s['2.0']:+.2f} ({r['seat_won']['seat']['1.0']}, {r['seat_lost_to_pull']['1.0']}) | "
          f"{r['seat']['seat_first']['1.0']:+.2f} | {day(r['first'])}..{day(r['last'])} | {notes(r)} |")
print("\nPre-fleet outsider cases (verified outsiders who bought before the operator's first buy):")
for r in res:
    for c in r["cases"]:
        wi = "; ".join(f"{w[:8]} {x.get('cls')} n={x.get('n')} funder={(x.get('funder') or '?')[:8]}" for w, x in c["wallet_info"].items())
        print(f"- {r['key'][:50]} pool {c['pool'][:10]}: {c['sol']} SOL (max {c['max']}) from +{c['first_s']}s, held {c['held_sol']} into the fleet; "
              f"fleet came {c['fleet_came']} ({c['fleet_sol']:.2f} SOL, x{f(c.get('fleet_sol_vs_line'))} of the line's usual), pull at "
              f"{c['pull_min']:.1f} min (line {c['ref_pull_min']:.1f}), {c['pull_delay_s']} s after the outsider -> {c['outcome']} | {wi}")
print("\nReaction to outsider buys after the fleet started (n, pulled within 60 s, median delay to the pull in s):")
for r in res:
    if r["reaction"]:
        print(f"- {r['key'][:50]}: " + ", ".join(f"{b}: {v['n']}, {v['pulled_within_60s']}, {v['median_delay_s']}" for b, v in sorted(r["reaction"].items())))
