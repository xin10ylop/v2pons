#!/usr/bin/env python3
"""lines.py census7.json: the census grouped into candidate pump-and-pull lines. A line is a funder that fed 3+ pool creators, a creator
with 3+ pools, or an exact SOL amount used 5+ times. Per group: pools, distinct creators, fresh creators (under 20 transactions), the SOL
put in, pulled (the LP mint moved after the creation and the SOL vault now holds under 5% of it), the minutes to the pull, the span."""
import json, sys, collections, statistics as st

d = json.load(open(sys.argv[1])); P = [p for p in d["pools"] if p.get("sol")]
print(f"{len(d['pools'])} pools, {len(P)} with a SOL side, over {d['days']} days; by program: {dict(collections.Counter(p['kind'] for p in P))}")


def pulled(p):
    return bool(p.get("lp_later")) and p.get("sol_now") is not None and p["sol_now"] < 0.05 * p["sol"]


def mins(p):
    return (p["lp_later"][0] - p["t"]) / 60 if p.get("lp_later") else None


def show(title, groups, min_n):
    rows = []
    for key, ps in groups.items():
        if len(ps) < min_n:
            continue
        pu = [p for p in ps if pulled(p)]; m = [mins(p) for p in pu if mins(p) is not None]
        rows.append((len(ps), key, len({p["creator"] for p in ps}), sum((p.get("n") or 0) < 20 for p in ps), sorted(round(p["sol"], 3) for p in ps),
                     len(pu), st.median(m) if m else None, (max(p["t"] for p in ps) - min(p["t"] for p in ps)) / 3600))
    print(f"\n== {title} ({len(rows)} groups)")
    for n, key, nc, fresh, sols, npu, mpull, span in sorted(rows, reverse=True)[:15]:
        sol_txt = f"{sols[0]}" if sols[0] == sols[-1] else f"{sols[0]}-{sols[-1]} (median {st.median(sols)})"
        print(f"  {str(key)[:44]:44s} pools {n:3d} creators {nc:3d} fresh {fresh:3d} | SOL {sol_txt} | pulled {npu}/{n}"
              + (f", median {mpull:.1f} min after" if mpull is not None else "") + f" | over {span:.0f} h")


def group(key):
    g = collections.defaultdict(list)
    for p in P:
        g[key(p)].append(p)
    return g


show("by the creators' funder", group(lambda p: p.get("funder") or "?"), 3)
show("by creator", group(lambda p: p["creator"]), 3)
show("by the exact SOL amount", group(lambda p: round(p["sol"], 4)), 5)
pu = [p for p in P if pulled(p)]; m = sorted(mins(p) for p in pu if mins(p) is not None)
print(f"\nall pools: pulled {len(pu)}/{len(P)}; minutes to the pull: p10 {m[len(m)//10]:.1f}, median {st.median(m):.1f}, p90 {m[len(m)*9//10]:.1f}" if m else "")
