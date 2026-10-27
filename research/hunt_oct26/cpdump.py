#!/usr/bin/env python3
"""cpdump.py CHAIN SHAPE OUT DAY...: the counterparty of every swap in the pulled pools of one line (shape prefix, NIN env as in tolerance.py),
through the pool token's Transfer logs as in pnlfast.py, so later scripts can tell the line's machine from dust and strangers in every pool
without a per-transaction lookup. Writes OUT (gzip json): {day: {pool id: [counterparty or null, per event index]}}. Read-only, public RPCs."""
import os, sys, json, gzip, collections
import hlib as H

T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
NIN = {float(x) for x in os.environ["NIN"].split(",")} if os.environ.get("NIN") else None


def main(ch, shape, out, days):
    here = os.path.dirname(os.path.abspath(__file__))
    res = {}
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt"))
        cen = {p["id"]: p for p in json.load(open(os.path.join(here, f"out/{ch}_{day}_00.json")))["chains"][ch]["rugs"]}
        pools = {pid: p for pid, p in d["pools"].items() if pid in cen and p["shape"].startswith(shape)
                 and (NIN is None or round(p["nin"] or 0, 2) in NIN)}
        holder = {pid: (cen[pid]["pm"] if p["venue"] == "v4" else pid[3:]).lower() for pid, p in pools.items()}
        tok = {pid: cen[pid]["tok"].lower() for pid in pools}
        toks = sorted(set(tok.values())); n = 300 if ch == "rh" else 10
        xfer = collections.defaultdict(list)
        for i in range(0, len(toks), n):
            grp = set(toks[i:i + n]); ps = [p for pid, p in pools.items() if tok[pid] in grp]
            for x in H.logs(ch, min(p["bn"] for p in ps), max(p["pull"] for p in ps) + 2, [T], sorted(grp)):
                xfer[(x["transactionHash"], x["address"].lower())].append((H.a_of(x["topics"][1]), H.a_of(x["topics"][2])))
        res[day] = {}
        for pid, p in pools.items():
            hd = holder[pid]; cps = []
            for e in p["ev"]:
                cps.append(next((t if e[2] > 0 else f for f, t in xfer.get((e[6], tok[pid]), []) if (e[2] > 0 and f == hd) or (e[2] < 0 and t == hd)), None))
            res[day][pid] = cps
        print(f"  {ch} {day}: {len(pools)} pools, {sum(len(v) for v in res[day].values())} swaps, "
              f"{sum(c is None for v in res[day].values() for c in v)} unattributed", flush=True)
    json.dump(res, gzip.open(os.path.join(here, out), "wt"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
