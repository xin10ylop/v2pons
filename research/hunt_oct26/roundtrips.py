#!/usr/bin/env python3
"""roundtrips.py CENSUS.json OUT.json: who makes money at the front of pump-and-pull pools, whoever runs the pools and whoever trades them.

No operator, line, fleet or wallet is assumed. For every pulled pool of a census.py window, every swap from the creation to the pull; a
round trip is a buy of X tokens and a later sell of exactly X tokens (the integer amount) in the same pool before the pull, matched from the
logs alone. Per round trip: the entry and exit in seconds after the liquidity add, the native paid and the native profit, and the native
other buyers put in between the two legs (what it sold into). Only then is the buyer looked up (the buy transaction's sender and target).

Prints the wallets with profitable early round trips (entry within EARLY_S seconds of the add, default 20) over several pools, and the
pool families they hit (venue, fee/tick spacing, launch size, launch target), with counts, win rate and profit. A family where outsiders
win round after round is a front seat that is or was open, whoever operates it. Read-only, public RPCs."""
import os, sys, json, collections, statistics as st
import hlib as H

EARLY_S = float(os.environ.get("EARLY_S", "20"))


def fetch(ch, rugs):
    """every swap log of the pulled pools, from their creation to the pull (+2 blocks)"""
    c = H.CH[ch]; out = []
    for venue, topic in (("v4", H.T_SWAP4), ("v2", H.T_SWAP2), ("v3", H.T_SWAP3)):
        ps = sorted((p for p in rugs if p["venue"] == venue), key=lambda p: p["bn"])
        n = 150 if venue == "v4" else (300 if ch == "rh" else 10)        # Base's publicnode: at most ~10 addresses a query
        for i in range(0, len(ps), n):
            g = ps[i:i + n]; lo, hi = g[0]["bn"], max(p["rem_bn"] for p in g) + 2
            if venue == "v4":
                out += H.logs(ch, lo, hi, [topic, [p["id"][3:] for p in g]], c["pm"])
            else:
                out += H.logs(ch, lo, hi, [topic], [p["id"][3:] for p in g])
    return out


def legs(p, L):
    ev = []
    for x in L:
        d = x["data"][2:]; bn = int(x["blockNumber"], 16)
        if bn > p["rem_bn"]:
            continue
        if p["venue"] == "v2":
            a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
            nat = (a0i - a0o) if p["nat"] == 0 else (a1i - a1o)
            tok = (a1o - a1i) if p["nat"] == 0 else (a0o - a0i)
        elif p["venue"] == "v4":
            a0, a1 = H.i256(d[0:64]), H.i256(d[64:128])
            nat, tok = (-a0, a1) if p["nat"] == 0 else (-a1, a0)
        else:
            a0, a1 = H.i256(d[0:64]), H.i256(d[64:128])
            nat, tok = (a0, -a1) if p["nat"] == 0 else (a1, -a0)
        ev.append({"bn": bn, "li": int(x["logIndex"], 16), "nat": nat / 1e18, "tok": tok, "tx": x["transactionHash"]})
    return sorted(ev, key=lambda e: (e["bn"], e["li"]))


def match(p, ev, bt):
    a0 = p.get("add_bn", p["bn"]); trips = []; used = set()
    for i, b in enumerate(ev):
        if b["nat"] <= 0 or b["tok"] <= 0:
            continue
        for j in range(i + 1, len(ev)):
            s = ev[j]
            if j in used or s["nat"] >= 0 or -s["tok"] != b["tok"]:
                continue
            used.add(j)
            between = [e["nat"] for e in ev[i + 1:j] if e["nat"] > 0]
            trips.append({"pool": p["id"], "in_s": round((b["bn"] - a0) * bt, 1), "out_s": round((s["bn"] - a0) * bt, 1),
                          "pull_s": round((p["rem_bn"] - a0) * bt, 1), "paid": b["nat"], "pnl": -s["nat"] - b["nat"],
                          "others_in": sum(between), "biggest_in": max(between, default=0.0), "buy_tx": b["tx"], "sell_tx": s["tx"]})
            break
    return trips


def family(p):
    return (f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", H.ZERO) != H.ZERO else ""),
            float(f"{(p.get('nat_in') or 0):.2g}"), p.get("to"))


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
    trips = []
    for k, xs in per.items():
        p = by_id[k]
        for t in match(p, legs(p, xs), bt):
            t["fam"] = family(p); t["launcher"] = p.get("frm"); trips.append(t)
    print(f"{ch} {r.get('window')}: {len(rugs)} pulled pools, {len(L)} swaps, {len(trips)} round trips", flush=True)
    early = [t for t in trips if t["in_s"] <= EARLY_S]
    txs = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [t["buy_tx"]]) for t in early], workers=3)
    for t, x in zip(early, txs):
        t["who"] = x["from"].lower() if x else None; t["via"] = (x.get("to") or "").lower() if x else None
    W = collections.defaultdict(list)
    for t in early:
        if t.get("who") and t["who"] != t["launcher"]:
            W[t["who"]].append(t)
    rows = []
    for w, ts in W.items():
        pnl = sum(t["pnl"] for t in ts); wins = sum(t["pnl"] > 0 for t in ts)
        fams = collections.Counter(t["fam"] for t in ts)
        rows.append({"who": w, "trips": len(ts), "pools": len({t["pool"] for t in ts}), "wins": wins, "pnl": pnl, "paid": sum(t["paid"] for t in ts),
                     "in_s": st.median(t["in_s"] for t in ts), "out_s": st.median(t["out_s"] for t in ts),
                     "via": collections.Counter(t["via"] for t in ts).most_common(1)[0][0], "fams": [[list(k), v] for k, v in fams.most_common(4)]})
    rows.sort(key=lambda x: -x["pnl"])
    print(f"  early round trips (entry <= {EARLY_S:g} s): {len(early)} by {len(W)} wallets; profitable wallets with 3+ pools:", flush=True)
    for x in rows:
        if x["pools"] >= 3 and x["pnl"] > 0:
            print(f"    {x['who']} pools {x['pools']:4d} won {x['wins']:4d}/{x['trips']:<4d} pnl {x['pnl']:+.5f} on {x['paid']:.4f} | in {x['in_s']}s out {x['out_s']}s"
                  f" via {x['via'][:12] if x['via'] else '-'} | {x['fams'][0][0][0]} x {x['fams'][0][0][1]} via {(x['fams'][0][0][2] or '-')[:12]} ({x['fams'][0][1]})", flush=True)
    F = collections.defaultdict(list)
    for t in early:
        if t.get("who") and t["who"] != t["launcher"]:
            F[t["fam"]].append(t)
    print("  families with early outside round trips:", flush=True)
    fam_rows = []
    for k, ts in sorted(F.items(), key=lambda kv: -sum(t["pnl"] for t in kv[1])):
        pools = len({t["pool"] for t in ts}); n_f = sum(1 for p in rugs if family(p) == k)
        fam_rows.append({"fam": list(k), "pools_pulled": n_f, "pools_hit": pools, "trips": len(ts), "wins": sum(t["pnl"] > 0 for t in ts),
                         "pnl": sum(t["pnl"] for t in ts), "wallets": len({t["who"] for t in ts}), "pnl_med": st.median(t["pnl"] / t["paid"] for t in ts)})
        if pools >= 3:
            f = fam_rows[-1]
            print(f"    {k[0]:24s} x {k[1]:<8g} via {(k[2] or '-')[:14]:14s} pulled {n_f:5d} hit {pools:4d} trips {len(ts):5d} won {f['wins']:5d}"
                  f" pnl {f['pnl']:+.5f} median {f['pnl_med']:+.1%} wallets {f['wallets']}", flush=True)
    json.dump({"chain": ch, "window": r.get("window"), "bt": bt, "n_rugs": len(rugs), "n_trips": len(trips), "wallets": rows, "families": fam_rows,
               "early": early}, open(out, "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
