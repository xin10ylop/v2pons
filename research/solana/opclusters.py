#!/usr/bin/env python3
"""opclusters.py CENSUS.json SCANDIR OUT.json: operators that fund their creators through exchanges, found by where the money goes
(linescan.py fetch's outflows/ and hubs.json; with HELIUS_API_KEY set, every destination shared by 2+ creators is hub-checked first).

An exchange withdrawal hides the funder, but a deposit address belongs to one exchange account: creators that send their pull
proceeds to the same address, or send SOL to each other, are one operator. Destinations left out: the pool-creation fee accounts, hubs
(1000 signatures in under 3 days), and addresses that receive from more than MAX_FANIN creators (a service). Creators are joined
(union-find); a cluster with 3+ pools and 2+ creators is written to OUT as {name: [creators]} for linescan.py (OPS=OUT), and printed
with its pools, SOL sizes, dates and the lines it overlaps."""
import json, os, sys, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FEE_ACCOUNTS = {"DNXgeM9EiiaAbaWvwjHj9fQQLAX5ZsfHyvmYUNRAdNC8", "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eqaYcHQqtj2G5"}
MAX_FANIN = 25; MIN_SOL = 1.0


def main(census, scandir, out):
    pools = [p for p in json.load(open(census))["pools"] if p.get("sol")]
    by_creator = collections.defaultdict(list)
    for p in pools:
        by_creator[p["creator"]].append(p)
    hubs = json.load(open(f"{scandir}/hubs.json"))
    flows = {}
    for f in os.listdir(f"{scandir}/outflows"):
        a = f[:-5]
        if a in by_creator:
            flows[a] = {k: sum(x for _, x in v) for k, v in json.load(open(f"{scandir}/outflows/{f}")).get("sent", {}).items()}
    fanin = collections.Counter(d for fl in flows.values() for d, s in fl.items() if s >= MIN_SOL)
    shared = [d for d, k in fanin.items() if k >= 2 and d not in hubs and d not in FEE_ACCOUNTS]
    if shared and os.environ.get("HELIUS_API_KEY"):                 # a destination shared by 2+ creators: is it a busy service?
        import linescan as LS
        for d in shared:
            try:
                hubs[d] = LS.hub_check(d)
            except Exception:
                pass
        json.dump(hubs, open(f"{scandir}/hubs.json", "w"))
        print(f"hub-checked {len(shared)} shared destinations: {sum(1 for d in shared if hubs.get(d, {}).get('hub'))} are busy services", flush=True)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    via = collections.defaultdict(set)
    for c, fl in flows.items():
        for d, s in fl.items():
            if s < MIN_SOL or d in FEE_ACCOUNTS or hubs.get(d, {}).get("hub") or fanin[d] > MAX_FANIN:
                continue
            if d in flows:                                     # a creator paying another creator
                parent[find(c)] = find(d); via[(c, d)].add("creator to creator")
            elif fanin[d] >= 2:                                # two or more creators paying one address
                parent[find(c)] = find("dest:" + d)
    groups = collections.defaultdict(set)
    for c in flows:
        groups[find(c)].add(c)
    res, n = {}, 0
    day = lambda t: time.strftime("%m-%d", time.gmtime(t))
    for g in sorted(groups.values(), key=lambda g: -sum(len(by_creator[c]) for c in g)):
        ps = [p for c in g for p in by_creator[c]]
        if len(g) < 2 or len(ps) < 3:
            continue
        n += 1; name = f"op{n:02d}"; res[name] = sorted(g)
        dests = collections.Counter(d for c in g for d, s in flows[c].items() if s >= MIN_SOL and fanin[d] >= 2 and d not in FEE_ACCOUNTS
                                    and not hubs.get(d, {}).get("hub") and fanin[d] <= MAX_FANIN)
        sizes = collections.Counter(round(p["sol"], 2) for p in ps)
        funders = collections.Counter((p.get("funder") or "?")[:8] + ("(hub)" if hubs.get(p.get("funder") or "", {}).get("hub") else "") for p in ps)
        print(f"{name}: {len(ps)} pools by {len(g)} creators, {day(min(p['t'] for p in ps))}..{day(max(p['t'] for p in ps))}, SOL {dict(sizes.most_common(6))}; "
              f"funders {dict(funders.most_common(4))}; shared destinations {[(d[:8], k) for d, k in dests.most_common(4)]}")
    json.dump(res, open(out, "w"))
    print(f"{n} clusters -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
