#!/usr/bin/env python3
"""dammreport.py CENSUS.json PULLS.json CHAINS.json [MIN_POOLS]: the DAMM v2 census as linereport.py-style markdown (offline).

Lines: a creator with MIN_POOLS+ direct SOL pools (default 3), and operator chains (dammchain.py: creators linked by the SOL each one
sends, through a single-use relay, to the next; the funder line of linescan.py, since these creators' first funders are 5000+
signatures back). Columns
as in linereport30.md where the data exist; the trade-based columns (pump, fleet, pre-fleet evidence, verdict, seat) need every
transaction of each pool (900-1000+ per 85-SOL pool), which was not read (Helius credits ran out; the public RPC serves one transaction
a call), so they show 'not read'. Added instead, from the pull transactions of up to 3 sampled pools per line (dammpull.py): the SOL in
the pool when the creator pulled minus the SOL it deposited (what buyers left behind, net), and minutes from creation to pull."""
import json, sys, time, collections, statistics as st

cen = json.load(open(sys.argv[1])); pulls = json.load(open(sys.argv[2])); chains = json.load(open(sys.argv[3]))
funders = {}
for c, l in chains.get("links", {}).items():
    if l.get("next"):
        funders.setdefault(l["next"], {"funder": c, "via": l.get("via"), "n": None})
MIN = int(sys.argv[4]) if len(sys.argv) > 4 else 3
pools = cen["pools"]
day = lambda t: time.strftime("%Y-%m-%d", time.gmtime(t))
med = lambda xs: st.median(xs) if xs else None
f = lambda x, d=2: "-" if x is None else f"{x:.{d}f}"
byc = collections.defaultdict(list)
for p in pools:
    byc[p["creator"]].append(p)
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for c, l in chains.get("links", {}).items():                      # chains from the links (also from a partial dammchain.py run)
    if l.get("next"):
        parent[find(l["next"])] = find(c)
grp = collections.defaultdict(list)
for c in parent:
    grp[find(c)].append(c)
chain_list = [sorted(v, key=lambda c: min((p["t"] for p in byc.get(c, [])), default=0)) for v in grp.values() if len(v) >= 2]
lines = [("creator", c, ps) for c, ps in byc.items() if len(ps) >= MIN]
lines += [("chain", "chain:" + ch[0], [p for c in ch for p in byc.get(c, [])]) for ch in chain_list]


def row(kind, lid, ps):
    ps = sorted(ps, key=lambda p: p["t"]); span = max(1.0, (ps[-1]["t"] - ps[0]["t"]) / 86400)
    sols = sorted({round(p["sol"], 2) for p in ps})
    pl = [pulls[p["sig"]] for p in ps if p["sig"] in pulls and pulls[p["sig"]].get("sol_at_pull") is not None]
    net = [x["sol_at_pull"] - x["sol_deposit"] for x in pl]; mins = [x["minutes"] for x in pl]
    fu = funders.get(lid, {}) if kind == "creator" else {}
    members = sorted({p["creator"] for p in ps})
    return {"kind": kind, "id": lid, "n": len(ps), "pulled": sum(p["pulled"] for p in ps), "per_day": len(ps) / span,
            "sol": sols, "sol_med": med([p["sol"] for p in ps]), "pull_min": mins, "net": net, "first": ps[0]["t"], "last": ps[-1]["t"],
            "creators": members, "funder": fu.get("funder") if fu else None, "sigs": fu.get("n") if fu else ps[0].get("n"),
            "ix": collections.Counter(p["ix"] for p in ps).most_common(1)[0][0]}


R = [row(*L) for L in lines]
R.sort(key=lambda r: -(med(r["net"]) or -1e9) * (r["n"] if r["net"] else 0))
tot = len(pools); big = [p for p in pools if p["sol"] >= 80]
print(f"# Meteora DAMM v2: direct pool creations, {day(cen['t0'])} + {cen['days']:.0f} days\n")
print(f"Creation marker `{cen['marker']}` (only creations touch it). Creations by caller/instruction: {cen['by_caller']}. "
      f"Direct with a SOL side: {tot}; pulled (position closed or SOL vault < 5% of the deposit) {sum(p['pulled'] for p in pools)}. "
      f"Pools of 80+ SOL: {len(big)} (token side 1,000,000,000 in {sum(1 for p in big if abs((p.get('v1_amt') if p.get('v0_mint') == 'So11111111111111111111111111111111111111112' else p.get('v0_amt') or 0) - 1e9) < 1)}), "
      f"pulled {sum(p['pulled'] for p in big)}, from {len({p['creator'] for p in big})} creators.\n")
pl = [(next(p for p in pools if p["sig"] == s), x) for s, x in pulls.items() if x.get("sol_at_pull") is not None]
for name, sel in (("80+ SOL", [(p, x) for p, x in pl if p["sol"] >= 80]), ("under 80 SOL", [(p, x) for p, x in pl if p["sol"] < 80])):
    if sel:
        nets = [x["sol_at_pull"] - x["sol_deposit"] for p, x in sel]
        print(f"- Sampled pulls, {name}: {len(sel)} pools; SOL at the pull minus the deposit: median {med(nets):+.2f}, mean {st.mean(nets):+.2f}, "
              f"positive {sum(1 for v in nets if v > 0)}/{len(nets)}; pulled by the creator {sum(1 for p, x in sel if x['by_creator'])}/{len(sel)}; "
              f"minutes to the pull: median {med([x['minutes'] for p, x in sel]):.1f}")
print("\n| # | line | pools (pulled) | /day | pool SOL | pump x (range) | fleet: wallets, pools, buys at +s | pull min (median of sampled) | "
      "SOL left at pull, sampled (median) | pre-fleet for/weak/against | verdict | seat 0.5 / 1 / 2 SOL | first-buy exit 1 SOL | active | notes |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, r in enumerate(R, 1):
    sols = f"{r['sol'][0]}" if len(r["sol"]) == 1 else f"{r['sol'][0]}-{r['sol'][-1]} ({len(r['sol'])} sizes)"
    notes = [f"{r['ix']} pools"]
    if r["kind"] == "chain":
        notes.append(f"{len(r['creators'])} creators in turn (each sends its SOL through a one-transaction relay to the next): "
                     + ", ".join("`" + c + "`" for c in r["creators"]))
    elif r["funder"]:
        notes.append(f"funded by the previous creator `{r['funder']}` via relay `{funders[r['id']].get('via')}`")
    elif r["sigs"] and r["sigs"] >= 1000:
        notes.append("creator has 1000+ signatures (first funder not walked back)")
    print(f"| {k} | `{r['id']}` ({r['kind']}) | {r['n']} ({r['pulled']}) | {r['per_day']:.1f} | {sols} | not read | not read | "
          f"{', '.join(f(x, 1) for x in r['pull_min']) or '-'} ({f(med(r['pull_min']), 1)}) | {', '.join(f'{x:+.1f}' for x in r['net']) or '-'} ({f(med(r['net']), 1)}) | "
          f"not read | not read | not read | not read | {day(r['first'])}..{day(r['last'])} | {'; '.join(notes)} |")
