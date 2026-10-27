#!/usr/bin/env python3
"""pnlfast.py CHAIN DAY...: pnlall.py without the per-transaction lookups. Every trader's realised profit in pump-and-pull pools, however it
exits, attributed through the pool token's own Transfer logs: in the transaction of each swap the token moves between the pool's holder (the
PoolManager for v4, the pair or pool for V2/V3) and the trader (its wallet, or its private router), so the other side of that transfer is the
trader. One log query covers hundreds of tokens.

Per trader (the transfer's counterparty) and pool: native in and out up to the pull; a position not sold by the pull is lost; a
counterparty that took out far more than it put in (a launcher, the pool's machinery) is left out of that pool. Prints the traders profitable
on MIN_DAYS (default 4) or more days with MIN_PNL (default 0.01) or more. Writes out/pnlfast_CHAIN.json. Read-only, public RPCs."""
import os, sys, json, gzip, collections, statistics as st
import hlib as H

MIN_DAYS = int(os.environ.get("MIN_DAYS", "4"))
MIN_PNL = float(os.environ.get("MIN_PNL", "0.01"))
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def main(ch, days):
    here = os.path.dirname(os.path.abspath(__file__))
    G = collections.defaultdict(list)
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")); bt = d["bt"]
        cen = {p["id"]: p for p in json.load(open(os.path.join(here, f"out/{ch}_{day}_00.json")))["chains"][ch]["rugs"]}
        pools = {pid: p for pid, p in d["pools"].items() if pid in cen}
        holder = {pid: (cen[pid]["pm"] if p["venue"] == "v4" else pid[3:]).lower() for pid, p in pools.items()}
        tok = {pid: cen[pid]["tok"].lower() for pid in pools}
        by_tok = collections.defaultdict(list)
        for pid in pools:
            by_tok[tok[pid]].append(pid)
        toks = sorted(by_tok); n = 300 if ch == "rh" else 10
        xfer = collections.defaultdict(list)                     # (tx, token) -> [(from, to)]
        for i in range(0, len(toks), n):
            grp = toks[i:i + n]
            lo = min(pools[pid]["bn"] for t in grp for pid in by_tok[t]); hi = max(pools[pid]["pull"] for t in grp for pid in by_tok[t]) + 2
            for x in H.logs(ch, lo, hi, [T], grp):
                xfer[(x["transactionHash"], x["address"].lower())].append((H.a_of(x["topics"][1]), H.a_of(x["topics"][2])))
        for pid, p in pools.items():
            hd, tk = holder[pid], tok[pid]
            pos = collections.defaultdict(lambda: [0.0, 0.0, None])
            for e in p["ev"]:
                if e[0] > p["pull"]:
                    continue
                cp = None
                for f, t in xfer.get((e[6], tk), []):
                    if e[2] > 0 and f == hd:
                        cp = t; break
                    if e[2] < 0 and t == hd:
                        cp = f; break
                if not cp or cp == p["frm"]:
                    continue
                x = pos[cp]
                if e[2] > 0:
                    x[0] += e[2]
                    if x[2] is None:
                        x[2] = e[0]
                else:
                    x[1] += -e[2]
            for cp, (bought, sold, fb) in pos.items():
                if bought <= 0 or sold > bought * 20:
                    continue
                G[cp].append({"day": day, "pool": pid, "bought": bought, "sold": sold, "pnl": sold - bought, "open": sold == 0,
                              "in_s": (fb - p["add"]) * bt, "shape": f"{p['shape']} x {round(p['nin'] or 0, 2):g}"})
        print(f"  {ch} {day}: {len(pools)} pools, {len(xfer)} token transfers", flush=True)
    rows = []
    for cp, ps in G.items():
        per = collections.defaultdict(float)
        for x in ps:
            per[x["day"]] += x["pnl"]
        rows.append({"id": cp, "pnl": sum(per.values()), "per_day": dict(per), "days": len(per), "pos_days": sum(v > 0 for v in per.values()),
                     "pools": len(ps), "wins": sum(x["pnl"] > 0 for x in ps), "open_at_pull": sum(x["open"] for x in ps),
                     "stake": st.median(x["bought"] for x in ps), "in_s": st.median(x["in_s"] for x in ps),
                     "shapes": collections.Counter(x["shape"] for x in ps).most_common(3)})
    rows.sort(key=lambda r: -r["pnl"])
    print(f"{ch} {days[0]}..{days[-1]}: {len(G)} traders; profitable on {MIN_DAYS}+ days with {MIN_PNL:g}+ total:")
    for r in rows:
        if r["pos_days"] < MIN_DAYS or r["pnl"] < MIN_PNL:
            continue
        print(f"  {r['id']}\n      pnl {r['pnl']:+.4f} | days +{r['pos_days']}/{r['days']}: " + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(r["per_day"].items()))
              + f"\n      pools {r['pools']} won {r['wins']} open at the pull {r['open_at_pull']} | stake {r['stake']:.5f} | in {r['in_s']:.0f}s | {r['shapes']}",
              flush=True)
    json.dump(rows, open(os.path.join(here, f"out/pnlfast_{ch}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
