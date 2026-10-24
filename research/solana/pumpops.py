#!/usr/bin/env python3
"""pumpops.py OUTDIR [MIN_LAUNCHES]: pump.fun repeat operators from pumpcensus.py's creations (read-only; HELIUS_API_KEY).

Groups the creations by fee payer (the creator) and prints how many creators there are by launch count. Creators with MIN_LAUNCHES
(default 5) or more SOL-quoted launches in the window are repeat creators; only these get a funder lookup: the oldest transaction of
the wallet (getTransactionsForAddress ascending, one call) and the sender of the first SOL into it (a System transfer to the creator;
if none, the fee payer of that transaction when it is another wallet). A funder shared by 2+ repeat creators is checked for being a
hub (1000+ signatures within 3 days: an exchange or a service), and creators sharing a non-hub funder are merged into one operator.
A fee payer whose launches name other wallets as the coin creator (the CreateEvent's creator field) in most of them is flagged as a
launch service (it creates for others). Writes OUTDIR/operators.json (operators with members, funder, launches) and
OUTDIR/creators_dist.json."""
import json, os, sys, time, glob, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P


def load(outdir):
    recs = []
    for f in sorted(glob.glob(outdir + "/creations/*.json")):
        recs += P.jload(f, {}).get("recs", [])
    return list({r["mint"]: r for r in recs}.values())


def funder(addr):
    txs, _ = P.gtfa(addr, asc=True, limit=5, max_pages=1, status=None)
    out = {"first_t": txs[0]["blockTime"] if txs else None, "funder": None, "funded_sol": None, "via": None}
    for tx in txs:
        if (tx.get("meta") or {}).get("err"):
            continue
        ks = P.keys(tx)
        for f, t, l in P.system_transfers(tx, ks):
            if t == addr and f != addr:
                out.update(funder=f, funded_sol=l / 1e9, via="transfer", t=tx["blockTime"]); return addr, out
        if ks[0] != addr:
            out.update(funder=ks[0], via="fee payer", t=tx["blockTime"]); return addr, out
    return addr, out


def hub_check(addr):
    s = P.rpc("getSignaturesForAddress", [addr, {"limit": 1000}])
    span = (s[0].get("blockTime") or 0) - (s[-1].get("blockTime") or 0) if s else 0
    return addr, {"n": len(s), "span_h": round(span / 3600, 1), "hub": len(s) >= 1000 and span < 3 * 86400}


def main(outdir, min_l):
    recs = load(outdir); win = P.jload(outdir + "/window.json")
    sol = [r for r in recs if r["sol_curve"]]
    byp = collections.defaultdict(list)
    for r in sol:
        byp[r["payer"]].append(r)
    allp = collections.Counter(r["payer"] for r in recs)
    buckets = [(1, 1), (2, 2), (3, 4), (5, 9), (10, 19), (20, 49), (50, 99), (100, 199), (200, 10 ** 9)]
    dist = []
    for a, b in buckets:
        ps = [p for p, rs in byp.items() if a <= len(rs) <= b]
        dist.append({"launches": f"{a}" if a == b else f"{a}-{b}" if b < 10 ** 9 else f"{a}+", "creators": len(ps), "launches_total": sum(len(byp[p]) for p in ps)})
    days = (win["t1"] - win["t0"]) / 86400
    print(f"{len(recs)} creations in {days:g} days ({len(recs) / days:.0f}/day); SOL-quoted curves {len(sol)} "
          f"({len(recs) - len(sol)} quoted in another token); {len(byp)} fee payers with SOL launches")
    print("creators by SOL-quoted launch count:")
    for d in dist:
        print(f"  {d['launches']:>7s}: {d['creators']:6d} creators, {d['launches_total']:6d} launches")
    rep = {p: rs for p, rs in byp.items() if len(rs) >= min_l}
    print(f"repeat creators (>= {min_l}): {len(rep)} with {sum(len(v) for v in rep.values())} launches", flush=True)
    fpath = outdir + "/funders.json"; fund = P.jload(fpath, {})
    need = [p for p in rep if p not in fund]
    with cf.ThreadPoolExecutor(6) as ex:
        for n, r in enumerate(ex.map(lambda a: _safe(funder, a), need)):
            if r:
                fund[r[0]] = r[1]
            if n % 100 == 0:
                print(f"  funders {n}/{len(need)} {dict(P.STATS)}", flush=True); P.jsave(fpath, fund)
    P.jsave(fpath, fund)
    byf = collections.defaultdict(set)
    for p in rep:
        f = (fund.get(p) or {}).get("funder")
        if f:
            byf[f].add(p)
    hpath = outdir + "/hubs.json"; hubs = P.jload(hpath, {})
    need = [f for f, cs in byf.items() if len(cs) >= 2 and f not in hubs]
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda a: _safe(hub_check, a), need):
            if r:
                hubs[r[0]] = r[1]
    P.jsave(hpath, hubs)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for f, cs in byf.items():
        if len(cs) >= 2 and not hubs.get(f, {}).get("hub"):
            cs = sorted(cs)
            for c in cs[1:]:
                parent[find(c)] = find(cs[0])
    groups = collections.defaultdict(list)
    for p in rep:
        groups[find(p)].append(p)
    ops = []
    for root, members in groups.items():
        ls = sorted((r for m in members for r in rep[m]), key=lambda r: (r["slot"], r["idx"] or 0))
        fs = sorted({(fund.get(m) or {}).get("funder") for m in members} - {None})
        svc = sum(1 for r in ls if r.get("creator") and r["creator"] != r["payer"])
        perday = collections.Counter(time.strftime("%m-%d", time.gmtime(r["t"])) for r in ls)
        dev = sorted(sum(b["sol"] + b["fee"] for b in r["buys"] if b["buy"] and b["user"] == r["payer"]) / 1e9 for r in ls)
        ops.append({"id": root, "members": sorted(members), "funders": fs, "funder_hub": {f: hubs.get(f, {}).get("hub") for f in fs},
                    "n": len(ls), "per_day": dict(sorted(perday.items())), "service_share": svc / len(ls),
                    "all_launches_incl_other_quote": sum(allp[m] for m in members),
                    "dev_buy_median": dev[len(dev) // 2] if dev else 0, "no_dev_buy": sum(1 for x in dev if x == 0),
                    "launches": [{k: r[k] for k in ("sig", "slot", "idx", "t", "payer", "mint", "curve", "creator", "name", "symbol", "buys", "txfee", "tip", "xfers", "nsig")}
                                 for r in ls]})
    ops.sort(key=lambda o: -o["n"])
    P.jsave(outdir + "/operators.json", ops)
    P.jsave(outdir + "/creators_dist.json", {"days": days, "n": len(recs), "sol": len(sol), "dist": dist,
                                             "merged": [{"id": o["id"], "members": o["members"], "funders": o["funders"]} for o in ops if len(o["members"]) > 1]})
    print(f"{len(ops)} operators after merging by funder ({sum(1 for o in ops if len(o['members']) > 1)} merged groups); "
          f"service-like fee payers (other coin creator in > 50%): {sum(1 for o in ops if o['service_share'] > 0.5)}")
    for o in ops[:40]:
        print(f"  {o['id'][:12]} members {len(o['members'])} launches {o['n']} {o['per_day']} dev {o['dev_buy_median']:.3f} "
              f"svc {o['service_share']:.2f} funder {[f[:8] for f in o['funders']]}")


def _safe(fn, a):
    try:
        return fn(a)
    except Exception as e:
        print(f"  lookup failed {a[:8]}: {str(e)[:80]}", flush=True)
        return None


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)
