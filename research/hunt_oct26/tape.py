#!/usr/bin/env python3
"""tape.py CENSUS.json OUT.json.gz: the full tape of a census.py window, for copy-trading research.

For every pulled pool: every swap from the creation to the pull (+2 blocks) with the pool's state after it, and every round trip (a buy of
X tokens and a later sell of exactly X tokens before the pull, roundtrips.py's match) with its buyer and seller resolved, early or not.

The state after each swap is the pool's native and token reserves:
  - V2: the pair's Sync event, read in the same query as its swaps;
  - V3 / v4: the virtual reserves of the active range from the swap's own sqrtPriceX96 and liquidity (x = L/sqrtP, y = L*sqrtP for
    currency0 / currency1), exact for a trade that stays inside the range.

out: {"chain", "window", "bt", "pools": {id: {venue, nat (native side 0/1), fee (fraction), bn, add, pull, nin, to, frm,
      ev: [[block, logIndex, native in (+ buy), token out (+ buy), native reserve, token reserve, tx], ...]}},
      "trips": [{pool, b (buy index), s (sell index), paid, pnl, who, via, sell_who}]}. Read-only, public RPCs."""
import sys, json, gzip, collections
import hlib as H
from roundtrips import match

T_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"   # Sync(uint112,uint112)
Q96 = 2 ** 96


def fetch(ch, rugs):
    c = H.CH[ch]; out = []
    for venue, topics in (("v4", [H.T_SWAP4]), ("v2", [[H.T_SWAP2, T_SYNC]]), ("v3", [[H.T_SWAP3, H.T_SWAP3_PCS]])):   # V3: Uniswap's or PancakeSwap's Swap
        ps = sorted((p for p in rugs if p["venue"] == venue), key=lambda p: p["bn"])
        n = 150 if venue == "v4" else (300 if ch == "rh" else 10)        # Base's publicnode: at most ~10 addresses a query
        for i in range(0, len(ps), n):
            g = ps[i:i + n]; lo, hi = g[0]["bn"], max(p["rem_bn"] for p in g) + 2
            if venue == "v4":
                out += H.logs(ch, lo, hi, topics + [[p["id"][3:] for p in g]], c["pm"])
            else:
                out += H.logs(ch, lo, hi, topics, [p["id"][3:] for p in g])
    return out


def events(p, L):
    """the pool's swaps in order, each with the reserves after it"""
    L = sorted(L, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    ev, sync = [], None
    for x in L:
        d = x["data"][2:]; bn = int(x["blockNumber"], 16)
        if bn > p["rem_bn"] + 2:
            continue
        if x["topics"][0] == T_SYNC:                       # V2: a pair emits Sync (its new reserves) just before the Swap
            r0, r1 = int(d[0:64], 16), int(d[64:128], 16)
            sync = (bn, int(x["logIndex"], 16), *((r0, r1) if p["nat"] == 0 else (r1, r0)))
            continue
        if p["venue"] == "v2":
            a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
            nat = (a0i - a0o) if p["nat"] == 0 else (a1i - a1o)
            tok = (a1o - a1i) if p["nat"] == 0 else (a0o - a0i)
            ok = sync and sync[0] == bn and sync[1] < int(x["logIndex"], 16)
            xr, yr = (sync[2] / 1e18, float(sync[3])) if ok else (None, None)
        else:
            a0, a1 = H.i256(d[0:64]), H.i256(d[64:128])
            if p["venue"] == "v4":
                nat, tok = (-a0, a1) if p["nat"] == 0 else (-a1, a0)
            else:
                nat, tok = (a0, -a1) if p["nat"] == 0 else (a1, -a0)
            s, liq = int(d[128:192], 16) / Q96, int(d[192:256], 16)
            if s > 0 and liq > 0:
                xr, yr = ((liq / s) / 1e18, liq * s) if p["nat"] == 0 else ((liq * s) / 1e18, liq / s)
            else:
                xr = yr = None
        ev.append([bn, int(x["logIndex"], 16), nat / 1e18, float(tok), xr, yr, x["transactionHash"], tok])
    return ev


def main(path, out):
    d = json.load(open(path)); ch = next(iter(d["chains"])); r = d["chains"][ch]; bt = r["bt"]
    rugs = [p for p in r["rugs"] if (p.get("nat_in") or 0) > 0]
    by_id = {p["id"][3:]: p for p in rugs}
    L = fetch(ch, rugs)
    per = collections.defaultdict(list)
    for x in L:
        k = x["topics"][1] if x["topics"][0] == H.T_SWAP4 else x["address"].lower()
        if k in by_id:
            per[k].append(x)
    pools, trips = {}, []
    for k, xs in per.items():
        p = by_id[k]
        ev = events(p, xs)
        fee = (p.get("fee") or 3000) if p["venue"] != "v2" else 3000
        fee = (fee if fee < 1 << 23 else 3000) / 1e6
        # roundtrips.match wants dicts with an integer token amount
        mev = [{"bn": e[0], "li": e[1], "nat": e[2], "tok": e[7], "tx": e[6]} for e in ev if e[0] <= p["rem_bn"]]
        idx = {(e[0], e[1]): i for i, e in enumerate(ev)}
        for t in match(p, mev, bt):
            b = next(i for i, e in enumerate(ev) if e[6] == t["buy_tx"] and e[2] > 0)
            s = next(i for i, e in enumerate(ev) if e[6] == t["sell_tx"] and e[2] < 0 and i > b)
            trips.append({"pool": p["id"], "b": b, "s": s, "paid": t["paid"], "pnl": t["pnl"]})
        pools[p["id"]] = {"venue": p["venue"], "nat": p["nat"], "fee": fee, "bn": p["bn"], "add": p.get("add_bn", p["bn"]), "pull": p["rem_bn"],
                          "nin": p.get("nat_in"), "to": p.get("to"), "frm": p.get("frm"), "shape": f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}"
                          + (" hook" if p.get("hooks", H.ZERO) != H.ZERO else ""), "ev": [e[:7] for e in ev]}
    txs = sorted({pools[t["pool"]]["ev"][t["b"]][6] for t in trips} | {pools[t["pool"]]["ev"][t["s"]][6] for t in trips})
    got = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [h]) for h in txs], size=50, workers=3)
    who = {h: ((x["from"].lower(), (x.get("to") or "").lower()) if x else (None, None)) for h, x in zip(txs, got)}
    for t in trips:
        ev = pools[t["pool"]]["ev"]
        t["who"], t["via"] = who[ev[t["b"]][6]]; t["sell_who"] = who[ev[t["s"]][6]][0]
    json.dump({"chain": ch, "window": r.get("window"), "bt": bt, "pools": pools, "trips": trips}, gzip.open(out, "wt"))
    print(f"{ch} {r.get('window')}: {len(pools)} pulled pools, {sum(len(p['ev']) for p in pools.values())} swaps, {len(trips)} round trips, "
          f"{sum(t['who'] is None for t in trips)} unresolved -> {out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
