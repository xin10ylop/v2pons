#!/usr/bin/env python3
"""pnlall.py CHAIN DAY...: every trader's realised profit in pump-and-pull pools from the tapes, however it exits: the sender of every swap
resolved (cached in out/who_CHAIN.json, saved as it goes), then per trader and pool its native in and out up to the pull. A position not sold
by the pull is lost; a trader that sold more than it bought in a pool (a launcher, the pool's own machinery) is left out of that pool.

Traders are grouped as in snipers.py (a private router with all its wallets, or a wallet on a public router). Prints those profitable on
MIN_DAYS (default 4) or more days with a total of MIN_PNL (default 0.01) or more: profit per day, pools, win rate, median stake, entry,
and how often a pool it entered was pulled with its position still open. Writes out/pnlall_CHAIN.json. Read-only, public RPCs."""
import os, sys, json, gzip, collections, statistics as st
import hlib as H
from snipers import PUBLIC

MIN_DAYS = int(os.environ.get("MIN_DAYS", "4"))
MIN_PNL = float(os.environ.get("MIN_PNL", "0.01"))
CHUNK = 20000


def resolve(ch, txs, cache, cache_p):
    todo = sorted(set(txs) - set(cache))
    for i in range(0, len(todo), CHUNK):
        part = todo[i:i + CHUNK]
        got = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [h]) for h in part], size=int(os.environ.get("BATCH", "50")),
                      workers=int(os.environ.get("WORKERS", "3")))
        for h, x in zip(part, got):
            if x:
                cache[h] = [x["from"].lower(), (x.get("to") or "").lower()]
        json.dump(cache, open(cache_p, "w"))
        print(f"  resolved {min(i + CHUNK, len(todo))}/{len(todo)}", flush=True)


def main(ch, days):
    here = os.path.dirname(os.path.abspath(__file__))
    cache_p = os.path.join(here, f"out/who_{ch}.json")
    try:
        cache = json.load(open(cache_p))
    except (OSError, ValueError):
        cache = {}
    G = collections.defaultdict(list)
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")); bt = d["bt"]
        resolve(ch, [e[6] for p in d["pools"].values() for e in p["ev"]], cache, cache_p)
        for pid, p in d["pools"].items():
            pos = collections.defaultdict(lambda: [0.0, 0.0, None, set()])   # key -> [bought, sold, first buy block, wallets]
            for e in p["ev"]:
                w = cache.get(e[6])
                if not w or e[0] > p["pull"]:
                    continue
                key = ("contract", w[1]) if w[1] and w[1] not in PUBLIC.get(ch, ()) else ("wallet", w[0])
                if w[0] == p["frm"]:
                    continue
                x = pos[key]; x[3].add(w[0])
                if e[2] > 0:
                    x[0] += e[2]
                    if x[2] is None:
                        x[2] = e[0]
                else:
                    x[1] += -e[2]
            for key, (bought, sold, fb, ws) in pos.items():
                if bought <= 0 or sold > bought * 20:              # never bought, or a seller of supply it did not buy here
                    continue
                G[key].append({"day": day, "pool": pid, "bought": bought, "sold": sold, "pnl": sold - bought, "open": sold == 0,
                               "in_s": (fb - p["add"]) * bt, "shape": f"{p['shape']} x {round(p['nin'] or 0, 2):g}", "wallets": len(ws)})
    rows = []
    for key, ps in G.items():
        per = collections.defaultdict(float)
        for x in ps:
            per[x["day"]] += x["pnl"]
        rows.append({"kind": key[0], "id": key[1], "pnl": sum(per.values()), "per_day": dict(per), "days": len(per),
                     "pos_days": sum(v > 0 for v in per.values()), "pools": len(ps), "wins": sum(x["pnl"] > 0 for x in ps),
                     "open_at_pull": sum(x["open"] for x in ps), "stake": st.median(x["bought"] for x in ps), "in_s": st.median(x["in_s"] for x in ps),
                     "shapes": collections.Counter(x["shape"] for x in ps).most_common(3), "wallets_per_pool": st.median(x["wallets"] for x in ps)})
    rows.sort(key=lambda r: -r["pnl"])
    print(f"{ch} {days[0]}..{days[-1]}: {len(G)} traders; profitable on {MIN_DAYS}+ days with {MIN_PNL:g}+ total:")
    for r in rows:
        if r["pos_days"] < MIN_DAYS or r["pnl"] < MIN_PNL:
            continue
        print(f"  {r['kind']:8s} {r['id']}\n      pnl {r['pnl']:+.4f} | days +{r['pos_days']}/{r['days']}: "
              + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(r["per_day"].items()))
              + f"\n      pools {r['pools']} won {r['wins']} open at the pull {r['open_at_pull']} | stake {r['stake']:.5f} | in {r['in_s']:.0f}s"
              f" | wallets a pool {r['wallets_per_pool']:g} | {r['shapes']}", flush=True)
    json.dump(rows, open(os.path.join(here, f"out/pnlall_{ch}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
