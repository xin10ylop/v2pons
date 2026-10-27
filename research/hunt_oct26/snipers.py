#!/usr/bin/env python3
"""snipers.py CHAIN DAY...: who makes money trading pump-and-pull pools, day after day, from the tapes (tape.py) of the days given
(YYYYMMDD). Every round trip, early or not, grouped by the trader: a private router or relay is one group with all its wallets; on a public
router each wallet is one group. Per group: profit per day, profitable days, trips, win rate, pools, the median stake, entry (seconds after
the liquidity add), hold (seconds) and the pool shapes it trades. "fleet-like" marks many wallets each in about one pool, the pattern of a
line's own machinery (the tick-spacing-1 line's router, the 2.433 bot router) rather than an outside trader.

Prints the groups profitable on at least MIN_DAYS days (default 4) with a total of at least MIN_PNL native (default 0.01), by total profit.
Writes out/snipers_CHAIN.json. Read-only (reads out/ only)."""
import os, sys, json, gzip, collections, statistics as st

PUBLIC = {"rh": {"0x8876789976decbfcbbbe364623c63652db8c0904", "0x89e5db8b5aa49aa85ac63f691524311aeb649eba"},
          "base": {"0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x6ff5693b99212da76ad316178a184ab56d299b43", "0x8cfe327cec66d1c090dd72bd0ff11d690c33a2eb",
                   "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x2626664c2603336e57b271c5c0b26f421741e481"}}
MIN_DAYS = int(os.environ.get("MIN_DAYS", "4"))
MIN_PNL = float(os.environ.get("MIN_PNL", "0.01"))


def key_of(ch, t):
    v = t.get("via") or ""
    return ("contract", v) if v and v not in PUBLIC.get(ch, ()) else ("wallet", t["who"])


def main(ch, days):
    here = os.path.dirname(os.path.abspath(__file__))
    G = collections.defaultdict(list)
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")); bt = d["bt"]; P = d["pools"]
        for t in d["trips"]:
            if not t.get("who"):
                continue
            p = P[t["pool"]]; b, s = p["ev"][t["b"]], p["ev"][t["s"]]
            G[key_of(ch, t)].append({"day": day, "pool": t["pool"], "who": t["who"], "paid": t["paid"], "pnl": t["pnl"], "shape": p["shape"],
                                     "size": round(p["nin"] or 0, 2), "in_s": (b[0] - p["add"]) * bt, "hold_s": (s[0] - b[0]) * bt,
                                     "to_pull_s": (p["pull"] - s[0]) * bt, "launcher": p["frm"]})
    rows = []
    for k, ts in G.items():
        per = collections.defaultdict(float)
        for t in ts:
            per[t["day"]] += t["pnl"]
        wallets = collections.Counter(t["who"] for t in ts); pools = {t["pool"] for t in ts}
        if any(t["who"] == t["launcher"] for t in ts) and sum(t["who"] == t["launcher"] for t in ts) > len(ts) / 2:
            continue                                         # the pool's own launcher trading its pool
        rows.append({"kind": k[0], "id": k[1], "pnl": sum(per.values()), "per_day": dict(per), "days": len(per), "pos_days": sum(v > 0 for v in per.values()),
                     "trips": len(ts), "wins": sum(t["pnl"] > 0 for t in ts), "pools": len(pools), "wallets": len(wallets),
                     "fleet_like": len(wallets) >= 10 and len(pools) / len(wallets) < 1.5,
                     "stake": st.median(t["paid"] for t in ts), "ret": st.median(t["pnl"] / t["paid"] for t in ts if t["paid"] > 0),
                     "in_s": st.median(t["in_s"] for t in ts), "hold_s": st.median(t["hold_s"] for t in ts), "margin_s": st.median(t["to_pull_s"] for t in ts),
                     "shapes": collections.Counter(f"{t['shape']} x {t['size']:g}" for t in ts).most_common(4), "top_wallets": wallets.most_common(3)})
    rows.sort(key=lambda r: -r["pnl"])
    print(f"{ch} {days[0]}..{days[-1]}: {sum(len(v) for v in G.values())} round trips, {len(G)} traders; profitable on {MIN_DAYS}+ days with {MIN_PNL:g}+ total:")
    for r in rows:
        if r["pos_days"] < MIN_DAYS or r["pnl"] < MIN_PNL:
            continue
        print(f"  {r['kind']:8s} {r['id']} {'FLEET-LIKE' if r['fleet_like'] else ''}\n"
              f"      pnl {r['pnl']:+.4f} | days +{r['pos_days']}/{r['days']}: " + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(r["per_day"].items()))
              + f"\n      trips {r['trips']} won {r['wins']} pools {r['pools']} wallets {r['wallets']} | stake {r['stake']:.5f} ret {r['ret']:+.0%}"
              f" | in {r['in_s']:.1f}s hold {r['hold_s']:.1f}s exit {r['margin_s']:.0f}s before the pull | {r['shapes'][:3]}", flush=True)
    json.dump(rows, open(os.path.join(here, f"out/snipers_{ch}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
