#!/usr/bin/env python3
"""allfront.py CHAIN OUT.json CENSUS.json...: the front seat searched in EVERY new pool, not only the pulled ones.

The 2.433 seat was a scripted buyer that bought blindly a few blocks after launch: buy before it, sell into it. Nothing about that needs a
rug, so this reads every native pool the census saw created (its "created" list: launchpads, locked-liquidity launches, market makers'
pairs and rugs alike), every swap from its creation to LIFE_S seconds later (env, default 1200), and roundtrips.py's match (a buy of X
tokens and a later sell of exactly X tokens) on each. Kept: round trips entered within EARLY_S seconds of the creation (default 30).

Then, only for the early round trips that made money at a real stake (MIN_PAID, default 0.001 native): the buyer, and the biggest buy that
landed between its two legs (what it sold into), each resolved to its transaction's sender and target. Prints:
  traders     wallets with profitable early round trips in 3+ pools: pools, trips, wins, profit, stake, in/out seconds, router
  sold into   the targets (bot contracts, routers) and senders of the buys those round trips sold into, by pools: a target that keeps
              buying behind early buyers across many pools is a 2.433-like bot, whoever runs it
  families    the pools hit, by venue, launch size band and whether they were pulled within 2 h
Read-only, public RPCs."""
import os, sys, json, collections, statistics as st
import hlib as H
from roundtrips import legs, match

LIFE_S = float(os.environ.get("LIFE_S", "1200")); EARLY_S = float(os.environ.get("EARLY_S", "30"))
MIN_PAID = float(os.environ.get("MIN_PAID", "0.001"))
WNATIVE = {"rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "base": "0x4200000000000000000000000000000000000006"}


def fetch(ch, P, life_blocks):
    c = H.CH[ch]; out = []
    for venue, topic in (("v4", H.T_SWAP4), ("v2", H.T_SWAP2), ("v3", H.T_SWAP3)):
        ps = sorted((p for p in P if p["venue"] == venue), key=lambda p: p["bn"])
        n = 150 if venue == "v4" else (300 if ch == "rh" else 10)
        for i in range(0, len(ps), n):
            g = ps[i:i + n]; lo, hi = g[0]["bn"], g[-1]["bn"] + life_blocks
            if venue == "v4":
                out += H.logs(ch, lo, hi, [topic, [p["id"][3:] for p in g]], c["pm"])
            else:
                out += H.logs(ch, lo, hi, [topic], [p["id"][3:] for p in g])
        print(f"  {venue}: {len(ps)} pools, {len(out)} swaps so far", flush=True)
    return out


def main(ch, out, files):
    P = {}; bt = None; pulled = set()
    for f in files:
        r = json.load(open(f))["chains"][ch]; bt = r["bt"]
        rug = {p["id"]: p for p in r["rugs"]}
        pulled |= set(rug)
        for key, tok, bn, tx, nin in r["created"]:
            venue = key.split(":")[0]
            if key in rug:
                p = dict(rug[key])
            else:
                p = {"id": key, "venue": venue, "bn": bn, "tok": tok, "nat_in": nin, "pm": H.CH[ch].get("pm"),
                     "nat": 0 if venue == "v4" else (0 if WNATIVE[ch] < tok.lower() else 1)}
            P[key] = p
    life = int(LIFE_S / bt)
    for p in P.values():
        p["rem_bn"] = min(p.get("rem_bn") or 10 ** 12, p["bn"] + life)
    print(f"{ch}: {len(P)} pools created ({len(pulled & set(P))} pulled within 2 h), {collections.Counter(p['venue'] for p in P.values())}", flush=True)
    L = fetch(ch, list(P.values()), life)
    per = collections.defaultdict(list)
    for x in L:
        k = ("v4:" + x["topics"][1]) if x["topics"][0] == H.T_SWAP4 else None
        if k is None:
            for v in ("v2", "v3"):
                if f"{v}:{x['address'].lower()}" in P:
                    k = f"{v}:{x['address'].lower()}"
        if k in P:
            per[k].append(x)
    trips = []
    for k, xs in per.items():
        p = P[k]; ev = legs(p, xs)
        if p["venue"] == "v4" and k not in pulled and ev:                     # a v4 pool on the wrapped token instead of ETH: the native leg is the small one
            first = next((e for e in ev if e["nat"] and e["tok"]), None)
            if first and abs(first["nat"]) * 1e18 > abs(first["tok"]):
                p["nat"] = 1; ev = legs(p, xs)
        for t in match(p, ev, bt):
            if t["in_s"] <= EARLY_S:
                t["pulled"] = k in pulled; t["nin"] = p.get("nat_in") or 0; t["venue"] = p["venue"]
                big = None
                for e in ev:
                    if e["tx"] == t["buy_tx"]:
                        b0 = e
                    if e["tx"] == t["sell_tx"]:
                        break
                for e in ev:
                    if (e["bn"], e["li"]) > (b0["bn"], b0["li"]) and e["nat"] > 0 and e["tx"] not in (t["buy_tx"], t["sell_tx"]):
                        if e["bn"] > next(x["bn"] for x in ev if x["tx"] == t["sell_tx"]):
                            break
                        if big is None or e["nat"] > big["nat"]:
                            big = e
                t["big_tx"] = big["tx"] if big else None; t["big_in"] = big["nat"] if big else 0.0
                trips.append(t)
    good = [t for t in trips if t["pnl"] > 0 and t["paid"] >= MIN_PAID]
    print(f"{ch}: {len(L)} swaps in {len(per)} pools; {len(trips)} early round trips (entry <= {EARLY_S:g} s), {len(good)} profitable at {MIN_PAID:g}+", flush=True)
    hs = sorted({t["buy_tx"] for t in good} | {t["big_tx"] for t in good if t["big_tx"]})
    txs = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [h]) for h in hs], size=50 if ch == "rh" else 10, workers=4 if ch == "rh" else 2, tries=10)
    tx = {h: x for h, x in zip(hs, txs) if x}
    for t in good:
        b = tx.get(t["buy_tx"]) or {}; g = tx.get(t["big_tx"]) or {}
        t["who"] = (b.get("from") or "").lower(); t["via"] = (b.get("to") or "").lower()
        t["big_who"] = (g.get("from") or "").lower(); t["big_via"] = (g.get("to") or "").lower(); t["big_sel"] = (g.get("input") or "")[:10]
    W = collections.defaultdict(list)
    for t in good:
        W[t["who"]].append(t)
    allw = collections.defaultdict(list)                                        # every early trip of those wallets, losers too
    for t in trips:
        pass
    print(f"\n  traders with profitable early round trips at {MIN_PAID:g}+ in 3+ pools:")
    for w, ts in sorted(W.items(), key=lambda kv: -sum(t["pnl"] for t in kv[1])):
        pools = {t["pool"] for t in ts}
        if len(pools) < 3:
            continue
        print(f"    {w} pools {len(pools):4d} trips {len(ts):4d} pnl {sum(t['pnl'] for t in ts):+.4f} on {sum(t['paid'] for t in ts):.3f} | stake median {st.median(t['paid'] for t in ts):.4f}"
              f" | in {st.median(t['in_s'] for t in ts):.1f}s out {st.median(t['out_s'] for t in ts):.1f}s | via {collections.Counter(t['via'] for t in ts).most_common(1)[0][0][:12]}"
              f" | pulled pools {sum(t['pulled'] for t in ts)}/{len(ts)} | venue {collections.Counter(t['venue'] for t in ts).most_common(2)}", flush=True)
    S = collections.defaultdict(list)
    for t in good:
        if t["big_via"]:
            S[(t["big_via"], t["big_sel"])].append(t)
    print(f"\n  what those round trips sold into (the biggest buy between their legs), by target and selector, 3+ pools:")
    for (via, sel), ts in sorted(S.items(), key=lambda kv: -len({t["pool"] for t in kv[1]})):
        pools = {t["pool"] for t in ts}
        if len(pools) < 3:
            continue
        print(f"    {via} {sel} pools {len(pools):4d} | its buy median {st.median(t['big_in'] for t in ts):.4f} | senders {len({t['big_who'] for t in ts})}"
              f" | front-runners {len({t['who'] for t in ts})}, their pnl {sum(t['pnl'] for t in ts):+.4f} on {sum(t['paid'] for t in ts):.3f}"
              f" | pulled pools {sum(t['pulled'] for t in ts)}/{len(ts)}", flush=True)
    F = collections.defaultdict(list)
    for t in good:
        band = "<0.5" if t["nin"] < 0.5 else "0.5-2" if t["nin"] < 2 else "2-10" if t["nin"] < 10 else "10+"
        F[(t["venue"], band, t["pulled"])].append(t)
    print(f"\n  pools hit, by venue, launch native and pulled within 2 h:")
    for k, ts in sorted(F.items(), key=lambda kv: -sum(t["pnl"] for t in kv[1])):
        print(f"    {k[0]} launch {k[1]:6s} {'pulled' if k[2] else 'kept  '} pools {len({t['pool'] for t in ts}):5d} trips {len(ts):5d} pnl {sum(t['pnl'] for t in ts):+.4f}"
              f" on {sum(t['paid'] for t in ts):.3f} | wallets {len({t['who'] for t in ts})}", flush=True)
    json.dump({"chain": ch, "files": files, "bt": bt, "n_pools": len(P), "n_trips": len(trips), "good": good,
               "early_all": [{k: t[k] for k in ("pool", "in_s", "out_s", "paid", "pnl", "big_in", "pulled", "venue", "buy_tx", "sell_tx")} for t in trips]},
              open(out, "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
