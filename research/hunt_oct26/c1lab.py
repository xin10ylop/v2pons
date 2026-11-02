#!/usr/bin/env python3
"""c1lab.py OUT.json DAY...: operator C-1 on Robinhood (or, with env FP=venue:selector:bytes and ROUTERS=a,b, any crowd operator whose
launches carry that fingerprint and whose crowd trades through those routers) (docs/HANDOFF.md 16.x: its own router 0xd6d35b56 and a wash crowd of 1,000+
wallets), re-tested on the census days given (out/rh_DAY_00.json).

C-1 launches with token-only liquidity (value 0), so the pulled-pool tools (tape.py, roundtrips.py: native in > 0) never saw it. Here:
  pools     every v4 pool created with 0 native whose launch is the PositionManager call ac9650d8 of 2,276 bytes (C-1's fingerprint),
            every swap from creation to its pull (or LIFE_S seconds, default 1200), reserves from each swap's price and liquidity
  router    the router's buys (transactions to 0xd6d35b56): first-buy offset, buys and ETH per pool
  outsiders swaps not through the router and not by the launcher: their first buys, size, pulled within 100 blocks (against pools of the
            same age without one), got out, profit
  ride      paper trades on the recorded reserves at STAKES (env, default 0.002,0.01,0.05), fee 0.01%: entry at the end of the router's
            first-buy block + K (1, 2, 3); exit after H blocks (20, 50, 100), or at +9% / +20%, or when the router has not bought for 20
            blocks (q20c100: 20 blocks, cap 100; q50c200 ...); a pull first = -100%. Per day, so a fading edge shows. Our own buy stays in the pool until we sell (the exit price includes our impact). Not
            modelled: a reaction to our own buy; the outsider rows test it, and "our slot" is outsiders buying 1-5 blocks after the router's
            first buy.
Read-only, public RPCs."""
import os, sys, json, math, bisect, collections, statistics as st
import hlib as H
from tape import events

ROUTERS = set(os.environ.get("ROUTERS", "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6").lower().split(","))
FP = os.environ.get("FP", "v4:0xac9650d8:2276").split(":"); FPV, FPS, FPL = FP[0], FP[1], int(FP[2])
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
LIFE_S = float(os.environ.get("LIFE_S", "1200")); GAS = 0.000006
STAKES = [float(x) for x in os.environ.get("STAKES", "0.002,0.01,0.05").split(",")]


def buy(x, y, s, FEE):
    return y - x * y / (x + s * (1 - FEE))


def sell(x, y, q, FEE):
    return x - x * y / (y + q * (1 - FEE))


def main(out, days):
    here = os.path.dirname(os.path.abspath(__file__)); url = H.CH["rh"]["rpc"]
    P = {}; bt = None
    for d in days:
        r = json.load(open(os.path.join(here, f"out/rh_{d}_00.json")))["chains"]["rh"]; bt = r["bt"]
        rug = {p["id"]: p for p in r["rugs"]}
        cand = [(k, tok, bn, tx) for k, tok, bn, tx, nin in r["created"] if k.startswith(FPV + ":") and (nin or 0) < 1e-6]
        txs = H.batch(url, [("eth_getTransactionByHash", [c[3]]) for c in cand], size=50, workers=4, tries=10)
        for (k, tok, bn, tx), t in zip(cand, txs):
            if t and t["input"][:10] == FPS and (len(t["input"]) - 2) // 2 == FPL:
                p = {"id": k, "venue": FPV, "nat": 0 if (FPV == "v4" or WETH < tok.lower()) else 1, "bn": bn, "tok": tok, "day": d,
                     "frm": t["from"].lower(), "pulled": k in rug}
                p["rem_bn"] = rug[k]["rem_bn"] if k in rug else bn + int(LIFE_S / bt)
                P[k] = p
        print(f"  {d}: {len(cand)} value-0 v4 launches, {sum(1 for p in P.values() if p['day'] == d)} with the fingerprint {FPV} {FPS} {FPL} B", flush=True)
    ps = sorted(P.values(), key=lambda p: p["bn"]); L = []
    for i in range(0, len(ps), 150 if FPV == "v4" else 300):
        g = ps[i:i + (150 if FPV == "v4" else 300)]
        if FPV == "v4":
            L += H.logs("rh", g[0]["bn"], max(p["rem_bn"] for p in g) + 2, [H.T_SWAP4, [p["id"][3:] for p in g]], H.CH["rh"]["pm"])
        else:
            L += H.logs("rh", g[0]["bn"], max(p["rem_bn"] for p in g) + 2, [H.T_SWAP3], [p["id"][3:] for p in g])
    per = collections.defaultdict(list)
    for x in L:
        per[("v4:" + x["topics"][1]) if FPV == "v4" else ("v3:" + x["address"].lower())].append(x)
    if FPV == "v3":                                            # a V3 pool's fee from the pool itself
        ks = sorted(P); fz = H.batch(url, [("eth_call", [{"to": k[3:], "data": "0xddca3f43"}, "latest"]) for k in ks], size=50, workers=2)
        for k, f in zip(ks, fz):
            P[k]["fee"] = int(f, 16) / 1e6 if f and f != "0x" else 0.01
    for k, p in P.items():
        p["ev"] = events(p, per.get(k, []))
        if FPV == "v4":
            fs = [int(x["data"][2:][320:384], 16) for x in per.get(k, []) if len(x["data"]) >= 2 + 384]
            p["fee"] = (st.median(fs) if fs else 100) / 1e6
    hs = sorted({e[6] for p in P.values() for e in p["ev"]})
    cache_p = os.path.join(here, "out/c1_tx.json" if ROUTERS == {"0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"} else "out/crowd_tx.json")
    try:
        tx = {h: tuple(v) for h, v in json.load(open(cache_p)).items()}
    except (OSError, ValueError):
        tx = {}
    todo = [h for h in hs if h not in tx or tx[h][0] is None]
    got = H.batch(url, [("eth_getTransactionByHash", [h]) for h in todo], size=50, workers=4, tries=10)
    tx.update({h: ((x["from"].lower(), (x.get("to") or "").lower()) if x else (None, None)) for h, x in zip(todo, got)})
    json.dump(tx, open(cache_p, "w"))
    print(f"rh {days[0]}..{days[-1]}: {len(P)} pools ({FPV} {FPS} {FPL} B, routers {sorted(r[:10] for r in ROUTERS)}) ({sum(p['pulled'] for p in P.values())} pulled within 2 h), {len(L)} swaps, "
          f"{sum(1 for h in hs if tx[h][0] is None)} unread transactions", flush=True)
    # router and outsiders
    first, rbuys, reth, outs, nofirst = [], [], [], [], 0
    lives = sorted((p["rem_bn"] - p["bn"]) for p in P.values() if p["pulled"])
    for p in P.values():
        ev = p["ev"]; rb = [e for e in ev if e[2] > 0 and tx[e[6]][1] in ROUTERS]
        p["r_first"] = rb[0][0] if rb else None
        if not rb:
            nofirst += 1; continue
        first.append(rb[0][0] - p["bn"]); rbuys.append(len(rb)); reth.append(sum(e[2] for e in rb))
        flows = collections.defaultdict(lambda: [None, 0.0, 0.0])
        for e in ev:
            w, v = tx[e[6]]
            if v in ROUTERS or w == p["frm"] or not w:
                continue
            f = flows[w]
            if e[2] > 0:
                f[1] += e[2]; f[0] = f[0] or e
            else:
                f[2] += -e[2]
        for w, (e0, b, s) in flows.items():
            if e0 is not None:
                outs.append({"who": w, "pool": p["id"], "bn": e0[0], "size": e0[2], "age": e0[0] - p["bn"], "after_r": e0[0] - rb[0][0],
                             "to_pull": (p["rem_bn"] - e0[0]) if p["pulled"] else None, "out": s > 0, "pnl": s - b})
    print(f"  router: first buy in {len(first)} pools (none in {nofirst}) at +{st.median(first):.0f} blocks median (p10 +{sorted(first)[len(first)//10]}, "
          f"p90 +{sorted(first)[9*len(first)//10]}) | buys per pool median {st.median(rbuys):.0f} | ETH per pool median {st.median(reth):.2f}, total {sum(reth):.1f}")
    for name, sel in (("dust < 0.001", lambda r: r["size"] < 0.001), ("real >= 0.001", lambda r: r["size"] >= 0.001)):
        rs = [r for r in outs if sel(r)]
        if not rs:
            print(f"  outsiders {name}: none"); continue
        pul = [r for r in rs if r["to_pull"] is not None]

        def base(age):                                   # share of C-1 pools alive at this age that were pulled within 100 more blocks
            alive = sum(1 for p in P.values() if (p["rem_bn"] - p["bn"]) > age or not p["pulled"])
            hit = sum(1 for p in P.values() if p["pulled"] and age < (p["rem_bn"] - p["bn"]) <= age + 100)
            return hit / alive if alive else 0
        print(f"  outsiders {name}: {len(rs)} buys by {len({r['who'] for r in rs})} wallets | pulled within 100 blocks {sum(1 for r in pul if r['to_pull'] <= 100) / len(rs):.0%}"
              f" (pools of that age: {sum(base(r['age']) for r in rs) / len(rs):.0%}) | got out {sum(r['out'] for r in rs) / len(rs):.0%}"
              f" | net {sum(r['pnl'] for r in rs):+.4f} | size median {st.median(r['size'] for r in rs):.4f}")
    cp = [r for r in outs if r["size"] >= 0.001 and 1 <= r["after_r"] <= 5]
    if cp:
        pul = [r for r in cp if r["to_pull"] is not None and r["to_pull"] <= 100]
        print(f"  outsiders in OUR slot (real size, 1-5 blocks after the router's first buy): {len(cp)} buys by {len({r['who'] for r in cp})} wallets | pulled within 100 blocks"
              f" {len(pul)} ({len(pul) / len(cp):.0%}) | got out {sum(r['out'] for r in cp) / len(cp):.0%} | net {sum(r['pnl'] for r in cp):+.4f} on {sum(r['size'] for r in cp):.4f}"
              f" | size median {st.median(r['size'] for r in cp):.4f}")
        for lo, hi in ((0.001, 0.01), (0.01, 0.05), (0.05, 99)):
            rs = [r for r in cp if lo <= r["size"] < hi]
            if rs:
                print(f"      size {lo:g}-{hi:g}: {len(rs)} buys, pulled within 100 blocks {sum(1 for r in rs if r['to_pull'] is not None and r['to_pull'] <= 100)}, got out {sum(r['out'] for r in rs)}")
    # ride
    rules = [(k, ex) for k in (1, 2, 3) for ex in ("h20", "h50", "h100", "h200", "tp9", "tp20", "q20c100", "q40c200", "q50c200", "q60c200", "q80c200")]
    res = {s: {r: collections.defaultdict(lambda: [0, 0, 0, 0.0]) for r in rules} for s in STAKES}
    for p in P.values():
        if p["r_first"] is None:
            continue
        ev = p["ev"]; bns = [e[0] for e in ev]; pull = p["rem_bn"] if p["pulled"] else 10 ** 12
        rb_blocks = sorted({e[0] for e in ev if e[2] > 0 and tx[e[6]][1] in ROUTERS})
        for k, ex in rules:
            eb = p["r_first"] + k
            if eb >= pull:
                continue
            i0 = bisect.bisect_right(bns, eb - 1) - 1
            if i0 < 0 or not ev[i0][4]:
                continue
            for s in STAKES:
                FEE = p["fee"]; q = buy(ev[i0][4], ev[i0][5], s, FEE); xb = None
                if ex.startswith("h"):
                    xb = eb + int(ex[1:])
                else:                                                    # (Nov 2 fix: the quiet clock runs per block, not per swap: in a pool where the
                    Q, cap = (int(ex[1:].split("c")[0]), eb + int(ex.split("c")[1])) if ex.startswith("q") else (None, eb + 100)   # router is the only trader, the next
                    j = i0 + 1; last_r = p["r_first"]                     # swap is its next buy, and a check made only at swaps never saw the gap)
                    while j < len(ev) and ev[j][0] < min(cap, pull):
                        if Q is not None and ev[j][0] > last_r + Q:          # Q blocks with no router buy before this swap's block: out at last_r + Q + 1
                            xb = last_r + Q + 1; break
                        if ev[j][0] in rb_blocks:
                            last_r = ev[j][0]
                        if ex.startswith("tp") and ev[j][4] and sell(ev[j][4] + s * (1 - FEE), ev[j][5] - q, q, FEE) >= s * (1 + int(ex[2:]) / 100):
                            xb = ev[j][0] + 1; break
                        j += 1
                    xb = xb or (last_r + Q + 1 if Q is not None and last_r + Q + 1 < cap else cap)
                r = res[s][(k, ex)][p["day"]]; r[0] += 1
                rt = res[s][(k, ex)][f"fee{round(p['fee'] * 1e6)}"]; rt[0] += 1
                if xb >= pull:
                    r[2] += 1; r[3] -= s + GAS; rt[2] += 1; rt[3] -= s + GAS; continue
                i1 = bisect.bisect_right(bns, xb - 1) - 1
                v = sell(ev[i1][4] + s * (1 - FEE), ev[i1][5] - q, q, FEE) - s - GAS   # our own buy still sits in the pool when we sell
                r[1] += v > 0; r[3] += v; rt[1] += v > 0; rt[3] += v
    for s in STAKES:
        print(f"\n  ride at {s:g} ETH (entry = router's first-buy block + K; pnl per day):")
        for k, ex in rules:
            dd = {d: v for d, v in res[s][(k, ex)].items() if not d.startswith("fee")}; n = sum(v[0] for v in dd.values()); pnl = sum(v[3] for v in dd.values())
            tiers = {d: v for d, v in res[s][(k, ex)].items() if d.startswith("fee")}
            print(f"    K{k} {ex:8s} n {n:4d} won {sum(v[1] for v in dd.values()):4d} pulled {sum(v[2] for v in dd.values()):3d} | pnl {pnl:+.4f} ({pnl / (n * s) if n else 0:+.1%} a trade)"
                  f" | " + " ".join(f"{d[4:]}:{dd[d][3]:+.3f}" for d in days if d in dd)
                  + " | by fee " + " ".join(f"{t}: n {v[0]} {v[3] / (v[0] * s) if v[0] else 0:+.1%}" for t, v in sorted(tiers.items())), flush=True)
    json.dump({"days": days, "pools": {k: {kk: v for kk, v in p.items() if kk != "ev"} for k, p in P.items()}, "outsiders": outs}, open(os.path.join(here, out), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
