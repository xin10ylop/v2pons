#!/usr/bin/env python3
"""routerlab.py CHAIN ROUTER OUT.json DAY...: c1lab.py for any private router, found from the logs alone.

A private router (an operator's own contract its wallet crowd trades through) calls the PoolManager itself, so it is the `sender` of
every v4 Swap it makes. Here:
  pools     every v4 pool the router swapped in during the census days (a Swap log with sender = ROUTER), with its creation block from
            the census "created" lists and its pull from the census rugs; every swap from creation to the pull (or LIFE_S, default 1200 s),
            reserves from each swap's price and liquidity
  router    its swaps by sender: first-buy offset, buys and native per pool
  outsiders swaps by any other sender, resolved to the transaction's sender (the launcher's left out): their first buys, size, pulled
            within 100 blocks (against pools of the same age), got out, profit; and those in OUR slot (1-5 blocks after the router's
            first buy)
  ride      paper trades on the recorded reserves at STAKES (default 0.002,0.01,0.05) at each pool's swap fee: entry at the end of the
            router's first-buy block + K (1, 2, 3); exit after H blocks (20, 50, 100), at +9% / +20%, or when the router has not bought
            for 20 blocks (cap 100); a pull first = -100%; our buy stays in the pool until we sell. Per day.
Read-only, public RPCs."""
import os, sys, json, math, bisect, collections, statistics as st
import hlib as H
from tape import events

LIFE_S = float(os.environ.get("LIFE_S", "1200")); GAS = {"rh": 0.000006, "base": 0.00002}
STAKES = [float(x) for x in os.environ.get("STAKES", "0.002,0.01,0.05").split(",")]
WN = {"rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "base": "0x4200000000000000000000000000000000000006"}


def main(ch, router, out, days):
    here = os.path.dirname(os.path.abspath(__file__)); router = router.lower(); pm = H.CH[ch]["pm"]; url = H.CH[ch]["rpc"]; gas = GAS[ch]
    created, rugs, bt, lo, hi = {}, {}, None, None, None
    for d in days:
        r = json.load(open(os.path.join(here, f"out/{ch}_{d}_00.json")))["chains"][ch]; bt = r["bt"]
        lo = r["from"] if lo is None else min(lo, r["from"]); hi = r["head"] if hi is None else max(hi, r["head"])
        for k, tok, bn, tx, nin in r["created"]:
            created[k] = (bn, tx, d)
        rugs.update({p["id"]: p for p in r["rugs"]})
    pad = "0x" + "0" * 24 + router[2:]
    R = H.logs(ch, lo, hi, [H.T_SWAP4, None, pad], pm)
    ids = sorted({"v4:" + x["topics"][1] for x in R} & set(created))
    print(f"{ch} router {router}: {len(R)} swaps in {len({x['topics'][1] for x in R})} pools, {len(ids)} of them created in the window", flush=True)
    P = {}
    for k in ids:
        bn, tx, d = created[k]
        P[k] = {"id": k, "venue": "v4", "bn": bn, "day": d, "tx": tx, "pulled": k in rugs, "rem_bn": rugs[k]["rem_bn"] if k in rugs else bn + int(LIFE_S / bt)}
    # the native side and fee from each pool's Initialize
    ps = sorted(P.values(), key=lambda p: p["bn"])
    for i in range(0, len(ps), 150):
        g = ps[i:i + 150]
        for x in H.logs(ch, g[0]["bn"], g[-1]["bn"], [H.T_INIT, [p["id"][3:] for p in g]], pm):
            p = P["v4:" + x["topics"][1]]; c0 = "0x" + x["topics"][2][26:]
            p["nat"] = 0 if c0 in (H.ZERO, WN[ch]) else 1; p["fee0"] = int(x["data"][2:66], 16)
    P = {k: p for k, p in P.items() if "nat" in p}
    L = []
    ps = sorted(P.values(), key=lambda p: p["bn"])
    for i in range(0, len(ps), 150):
        g = ps[i:i + 150]
        L += H.logs(ch, g[0]["bn"], max(p["rem_bn"] for p in g) + 2, [H.T_SWAP4, [p["id"][3:] for p in g]], pm)
    per = collections.defaultdict(list); rset = set()
    for x in L:
        per["v4:" + x["topics"][1]].append(x)
        if x["topics"][2][26:] == router[2:]:
            rset.add((x["transactionHash"], int(x["logIndex"], 16)))
    for k, p in P.items():
        xs = per.get(k, [])
        fs = [int(x["data"][2:][320:384], 16) for x in xs if len(x["data"]) >= 2 + 384]
        p["fee"] = (st.median(fs) if fs else (p["fee0"] if p["fee0"] < 0x800000 else 10000)) / 1e6
        p["ev"] = events(p, xs)
        p["is_r"] = [(e[6], e[1]) in rset for e in p["ev"]]
    # launchers and outsiders' senders
    hs = sorted({p["tx"] for p in P.values()} | {e[6] for p in P.values() for e, r in zip(p["ev"], p["is_r"]) if not r})
    got = H.batch(url, [("eth_getTransactionByHash", [h]) for h in hs], size=50 if ch == "rh" else 10, workers=4 if ch == "rh" else 2, tries=10)
    who = {h: (x["from"].lower() if x else None) for h, x in zip(hs, got)}
    print(f"  {len(P)} pools ({sum(p['pulled'] for p in P.values())} pulled within 2 h), {len(L)} swaps, router swaps {len(rset)}; fee {collections.Counter(round(p['fee'] * 1e6) for p in P.values()).most_common(3)}", flush=True)
    first, rb_n, rb_eth, outs, nof = [], [], [], [], 0
    for p in P.values():
        ev = p["ev"]; rb = [e for e, r in zip(ev, p["is_r"]) if r and e[2] > 0]
        p["r_first"] = rb[0][0] if rb else None
        if not rb:
            nof += 1; continue
        first.append(rb[0][0] - p["bn"]); rb_n.append(len(rb)); rb_eth.append(sum(e[2] for e in rb))
        launcher = who.get(p["tx"]); flows = collections.defaultdict(lambda: [None, 0.0, 0.0])
        for e, r in zip(ev, p["is_r"]):
            w = who.get(e[6])
            if r or not w or w == launcher:
                continue
            f = flows[w]
            if e[2] > 0:
                f[1] += e[2]; f[0] = f[0] or e
            else:
                f[2] += -e[2]
        for w, (e0, b, s) in flows.items():
            if e0 is not None:
                outs.append({"who": w, "pool": p["id"], "size": e0[2], "age": e0[0] - p["bn"], "after_r": e0[0] - rb[0][0],
                             "to_pull": (p["rem_bn"] - e0[0]) if p["pulled"] else None, "out": s > 0, "pnl": s - b})
    if not first:
        print("  the router never bought first in these pools"); return
    sf = sorted(first)
    print(f"  router: first buy in {len(first)} pools (none in {nof}) at +{st.median(first):.0f} blocks median (p10 +{sf[len(sf) // 10]}, p90 +{sf[9 * len(sf) // 10]})"
          f" | buys per pool median {st.median(rb_n):.0f} | native per pool median {st.median(rb_eth):.2f}, total {sum(rb_eth):.1f}")

    def base(age):
        alive = sum(1 for p in P.values() if (p["rem_bn"] - p["bn"]) > age or not p["pulled"])
        hit = sum(1 for p in P.values() if p["pulled"] and age < (p["rem_bn"] - p["bn"]) <= age + 100)
        return hit / alive if alive else 0
    for name, sel in (("dust < 0.001", lambda r: r["size"] < 0.001), ("real >= 0.001", lambda r: r["size"] >= 0.001),
                      ("real, in OUR slot (1-5 blocks after the router's first buy)", lambda r: r["size"] >= 0.001 and 1 <= r["after_r"] <= 5)):
        rs = [r for r in outs if sel(r)]
        if not rs:
            print(f"  outsiders {name}: none"); continue
        print(f"  outsiders {name}: {len(rs)} buys by {len({r['who'] for r in rs})} wallets | pulled within 100 blocks "
              f"{sum(1 for r in rs if r['to_pull'] is not None and r['to_pull'] <= 100) / len(rs):.0%} (pools of that age: {sum(base(r['age']) for r in rs) / len(rs):.0%})"
              f" | got out {sum(r['out'] for r in rs) / len(rs):.0%} | net {sum(r['pnl'] for r in rs):+.4f} on {sum(r['size'] for r in rs):.4f} | size median {st.median(r['size'] for r in rs):.4f}")
    rules = [(k, ex) for k in (1, 2, 3) for ex in ("h20", "h50", "h100", "tp9", "tp20", "quiet20")]
    for s in STAKES:
        print(f"\n  ride at {s:g} (entry = router's first-buy block + K; pnl per day):")
        for K, ex in rules:
            dd = collections.defaultdict(lambda: [0, 0, 0, 0.0])
            for p in P.values():
                if p["r_first"] is None:
                    continue
                ev = p["ev"]; bns = [e[0] for e in ev]; pull = p["rem_bn"] if p["pulled"] else 10 ** 12; f = p["fee"]
                rbl = sorted({e[0] for e, r in zip(ev, p["is_r"]) if r and e[2] > 0})
                eb = p["r_first"] + K
                if eb >= pull:
                    continue
                i0 = bisect.bisect_right(bns, eb - 1) - 1
                if i0 < 0 or not ev[i0][4]:
                    continue
                x0, y0 = ev[i0][4], ev[i0][5]; qty = y0 - x0 * y0 / (x0 + s * (1 - f))
                sl = lambda x, y: (x + s * (1 - f)) - (x + s * (1 - f)) * (y - qty) / (y - qty + qty * (1 - f))
                xb = None
                if ex.startswith("h"):
                    xb = eb + int(ex[1:])
                else:
                    cap = eb + 100; j = i0 + 1; last = p["r_first"]
                    while j < len(ev) and ev[j][0] < min(cap, pull):
                        if ev[j][0] in rbl:
                            last = ev[j][0]
                        if ex.startswith("tp") and ev[j][4] and sl(ev[j][4], ev[j][5]) >= s * (1 + int(ex[2:]) / 100):
                            xb = ev[j][0] + 1; break
                        if ex == "quiet20" and ev[j][0] - last > 20:
                            xb = ev[j][0] + 1; break
                        j += 1
                    xb = xb or (last + 21 if ex == "quiet20" and last + 21 < cap else cap)
                r = dd[p["day"]]; r[0] += 1
                if xb >= pull:
                    r[2] += 1; r[3] -= s + gas; continue
                i1 = bisect.bisect_right(bns, xb - 1) - 1
                v = sl(ev[i1][4], ev[i1][5]) - s - gas; r[1] += v > 0; r[3] += v
            n = sum(v[0] for v in dd.values()); pnl = sum(v[3] for v in dd.values())
            print(f"    K{K} {ex:8s} n {n:4d} won {sum(v[1] for v in dd.values()):4d} pulled {sum(v[2] for v in dd.values()):3d} | pnl {pnl:+.4f} ({pnl / (n * s) if n else 0:+.1%} a trade)"
                  f" | days +{sum(v[3] > 0 for v in dd.values())}/{len(dd)} | " + " ".join(f"{d[4:]}:{dd[d][3]:+.3f}" for d in days if d in dd), flush=True)
    json.dump({"router": router, "days": days, "outsiders": outs, "pools": {k: {kk: v for kk, v in p.items() if kk not in ("ev", "is_r")} for k, p in P.items()}},
              open(os.path.join(here, out), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
