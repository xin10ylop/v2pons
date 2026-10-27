#!/usr/bin/env python3
"""followers.py CHAIN KIND:ID DAY... : what happened to strangers in the pools a trader (snipers.py's group) trades: the reaction a copy of it
would meet, which the copy simulation cannot see.

Up to MAXPOOLS (env, default 120) of its pools, spread over the days; every swap's sender resolved (cached in out/who_CHAIN.json). Wallets:
  trader    the group's own (its router, or the wallet)
  machine   a pool's launch wallet; wallets buying in 3+ of the sampled pools; wallets behind a private router 10+ wallets call
  stranger  everyone else
Every stranger's real-size buy (REAL, default 0.001 native) and its fate: sold before the pull (its profit in the pool), or never sold (the
pull took it: -its buys). Split by position: within COPY_BLOCKS (default 2) blocks after one of the trader's buys (where our copy would land)
or elsewhere; and how soon the pull followed a stranger's buy, against the pools' usual life. Read-only, public RPCs."""
import os, sys, json, gzip, collections, statistics as st
import hlib as H
from snipers import PUBLIC

MAXPOOLS = int(os.environ.get("MAXPOOLS", "120"))
REAL = float(os.environ.get("REAL", "0.001"))
COPY_BLOCKS = int(os.environ.get("COPY_BLOCKS", "2"))


def main(ch, key, days):
    here = os.path.dirname(os.path.abspath(__file__))
    kind, ident = key.split(":", 1)
    cache_p = os.path.join(here, f"out/who_{ch}.json")
    try:
        cache = json.load(open(cache_p))
    except (OSError, ValueError):
        cache = {}
    pools, bt = {}, None
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")); bt = d["bt"]
        for t in d["trips"]:
            if (kind == "contract" and t.get("via") == ident) or (kind == "wallet" and t.get("who") == ident):
                pools.setdefault(t["pool"], d["pools"][t["pool"]])
    ids = sorted(pools, key=lambda k: pools[k]["bn"])
    ids = ids[:: max(1, len(ids) // MAXPOOLS)][:MAXPOOLS]
    txs = sorted({e[6] for k in ids for e in pools[k]["ev"]} - set(cache))
    got = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [h]) for h in txs], size=50, workers=3)
    for h, x in zip(txs, got):
        if x:
            cache[h] = [x["from"].lower(), (x.get("to") or "").lower()]
    json.dump(cache, open(cache_p, "w"))
    W = lambda e: cache.get(e[6], [None, None])
    trader = lambda w, v: (kind == "contract" and v == ident) or (kind == "wallet" and w == ident)
    buyers = collections.Counter(); via_w = collections.defaultdict(set)
    for k in ids:
        seen = set()
        for e in pools[k]["ev"]:
            w, v = W(e)
            if w and e[2] > 0:
                seen.add(w); via_w[v].add(w)
        for w in seen:
            buyers[w] += 1
    machine_via = {v for v, ws in via_w.items() if v and v not in PUBLIC.get(ch, ()) and len(ws) >= 10 and not (kind == "contract" and v == ident)}
    rows = []; pull_after = []; life = []
    for k in ids:
        p = pools[k]; ev = p["ev"]; pull = p["pull"]; life.append((pull - p["add"]) * bt)
        tbuys = [e[0] for e in ev if e[2] > 0 and trader(*W(e))]
        flows = collections.defaultdict(lambda: [0.0, 0.0, None, False])       # wallet -> [bought, sold, first buy block, copy position]
        for e in ev:
            w, v = W(e)
            if not w or trader(w, v) or w == p["frm"] or v in machine_via or buyers[w] >= 3:
                continue
            f = flows[w]
            if e[2] > 0:
                f[0] += e[2]
                if f[2] is None:
                    f[2] = e[0]; f[3] = any(0 <= e[0] - b <= COPY_BLOCKS for b in tbuys)
            elif e[0] <= pull:
                f[1] += -e[2]
        for w, (bought, sold, fb, cp) in flows.items():
            if bought < REAL or fb is None:
                continue
            rows.append({"pool": k, "who": w, "bought": bought, "sold": sold, "out": sold > 0, "pnl": sold - bought, "copy_pos": cp,
                         "to_pull_s": (pull - fb) * bt, "in_s": (fb - p["add"]) * bt})
            pull_after.append((pull - fb) * bt)
    print(f"{ch} {key}: {len(ids)} of {len(pools)} pools sampled, {len(cache)} transactions resolved; machine routers {len(machine_via)}, "
          f"recurring buyers {sum(c >= 3 for c in buyers.values())}; pool life median {st.median(life):.0f}s")
    for name, sel in (("all strangers", lambda r: True), (f"in the copy position (<= {COPY_BLOCKS} blocks after its buy)", lambda r: r["copy_pos"]),
                      ("elsewhere", lambda r: not r["copy_pos"])):
        rs = [r for r in rows if sel(r)]
        if not rs:
            print(f"  {name}: none"); continue
        out = [r for r in rs if r["out"]]
        print(f"  {name}: {len(rs)} real-size buys by {len({r['who'] for r in rs})} wallets in {len({r['pool'] for r in rs})} pools | got out {len(out)}"
              f" ({sum(r['pnl'] > 0 for r in out)} with a profit) | never sold {len(rs) - len(out)} | net {sum(r['pnl'] for r in rs):+.4f} on {sum(r['bought'] for r in rs):.4f}"
              f" | pull came a median {st.median(r['to_pull_s'] for r in rs):.0f}s after their buy (in at a median {st.median(r['in_s'] for r in rs):.0f}s)")
    json.dump(rows, open(os.path.join(here, f"out/followers_{ch}_{ident[:10]}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
