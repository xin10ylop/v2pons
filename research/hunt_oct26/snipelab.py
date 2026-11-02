#!/usr/bin/env python3
"""snipelab.py CHAIN HOOK DAY...: one v4 launchpad (its hook address), every pool it launched on the census days (out/CHAIN_DAY_00.json,
the "created" list), and what a sniper would have made on ALL of them, not only the winners.

  pools     every v4 pool created with token-only liquidity whose Initialize names HOOK: fee, tick spacing, the native currency side;
            its swaps for LIFE_S seconds (env, default 600) with the reserves after each (tape.events)
  crowd     per pool: the native bought in the creation block (the launcher's own bundled buy: unreachable), and by others in the first
            30 / 120 / 600 s
  sniper    our buy of STAKE (env STAKES, default 0.01,0.1,1) entering K blocks after the creation (1, 2, 3, 5, 10), priced two ways:
            first in that block (the state at the end of block K-1) and last in it (the end of block K); exit after 10 / 30 / 60 / 120 /
            300 s or at +20 / +50 / +100% (else at 300 s). The pool's fee both legs plus HOOK_FEE (env, default 0, a fraction) for
            whatever the hook takes; our buy stays in the pool until we sell. Mean, median, win rate and the share of the profit in the best
            10% of trades, per day.
Read-only, public RPCs."""
import os, sys, json, math, bisect, collections, statistics as st
import hlib as H
from tape import events

LIFE_S = float(os.environ.get("LIFE_S", "600")); HOOK_FEE = float(os.environ.get("HOOK_FEE", "0"))
STAKES = [float(x) for x in os.environ.get("STAKES", "0.01,0.1,1").split(",")]
WN = {"rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "base": "0x4200000000000000000000000000000000000006"}


def main(ch, hook, days):
    here = os.path.dirname(os.path.abspath(__file__)); hook = hook.lower(); pm = H.CH[ch]["pm"]
    P = {}; bt = None
    for d in days:
        r = json.load(open(os.path.join(here, f"out/{ch}_{d}_00.json")))["chains"][ch]; bt = r["bt"]
        cand = {k: (tok, bn) for k, tok, bn, tx, nin in r["created"] if k.startswith("v4:")}
        ids = sorted(cand, key=lambda k: cand[k][1])
        for i in range(0, len(ids), 150):
            g = ids[i:i + 150]
            for x in H.logs(ch, cand[g[0]][1], cand[g[-1]][1], [H.T_INIT, [k[3:] for k in g]], pm):
                dd = x["data"][2:]; hk = "0x" + dd[128 + 24:192]
                if hk != hook:
                    continue
                k = "v4:" + x["topics"][1]; c0 = "0x" + x["topics"][2][26:]
                P[k] = {"id": k, "venue": "v4", "bn": cand[k][1], "tok": cand[k][0], "day": d, "fee": int(dd[0:64], 16) / 1e6,
                        "nat": 0 if c0 in (H.ZERO, WN[ch]) else 1}
        print(f"  {d}: {len(cand)} v4 pools created, {sum(1 for p in P.values() if p['day'] == d)} with hook {hook[:10]}", flush=True)
    life = int(LIFE_S / bt)
    for p in P.values():
        p["rem_bn"] = p["bn"] + life
    ps = sorted(P.values(), key=lambda p: p["bn"]); L = []
    for i in range(0, len(ps), 100):
        g = ps[i:i + 100]
        L += H.logs(ch, g[0]["bn"], g[-1]["bn"] + life + 2, [H.T_SWAP4, [p["id"][3:] for p in g]], pm)
    per = collections.defaultdict(list)
    for x in L:
        per["v4:" + x["topics"][1]].append(x)
    for k, p in P.items():
        p["ev"] = events(p, per.get(k, []))
        p["fee0"] = round(p["fee"] * 1e6)
        if p["fee0"] >= 0x800000:                               # dynamic fee: the hook sets it per swap; the Swap event carries the one used
            fs = [int(x["data"][2:][320:384], 16) for x in per.get(k, []) if len(x["data"]) >= 2 + 384]
            p["fee"] = st.median(fs) / 1e6 if fs else 0.01
    fees = collections.Counter(p["fee0"] for p in P.values())
    print(f"  swap fees actually charged (dynamic pools, median per pool): {collections.Counter(round(p['fee'] * 1e6) for p in P.values() if p['fee0'] >= 0x800000).most_common(5)}")
    print(f"{ch} hook {hook}: {len(P)} pools over {len(days)} days, {len(L)} swaps | fee {fees.most_common(3)} | hook fee assumed {HOOK_FEE:.1%} a leg")
    cb, c30, c120, c600, n_any = [], [], [], [], 0
    for p in P.values():
        ev = p["ev"]
        cb.append(sum(e[2] for e in ev if e[2] > 0 and e[0] == p["bn"]))
        c30.append(sum(e[2] for e in ev if e[2] > 0 and p["bn"] < e[0] <= p["bn"] + 30 / bt))
        c120.append(sum(e[2] for e in ev if e[2] > 0 and p["bn"] < e[0] <= p["bn"] + 120 / bt))
        c600.append(sum(e[2] for e in ev if e[2] > 0 and p["bn"] < e[0]))
        n_any += any(e[0] > p["bn"] for e in ev)
    q = lambda v: f"median {st.median(v):.3f} p75 {sorted(v)[3 * len(v) // 4]:.3f} p90 {sorted(v)[9 * len(v) // 10]:.3f} max {max(v):.1f}"
    print(f"  native bought in the creation block (the launcher's bundle): {q(cb)} | pools with any later trade {n_any}/{len(P)}")
    print(f"  bought by others after it: first 30 s {q(c30)} | 120 s {q(c120)} | {LIFE_S:g} s {q(c600)}")
    for s in STAKES:
        print(f"\n  sniper at {s:g} (all {len(P)} pools; mean / median / win / top-10% share of the profit):")
        for K in (1, 2, 3, 5, 10):
            for pos in ("first", "last"):
                cells = []
                for ex in ("h10", "h30", "h60", "h120", "h300", "tp20", "tp50", "tp100"):
                    rets = []; per_day = collections.defaultdict(float)
                    for p in P.values():
                        ev = p["ev"]; bns = [e[0] for e in ev]; f = p["fee"] + HOOK_FEE
                        eb = p["bn"] + K; i0 = bisect.bisect_right(bns, eb - 1 if pos == "first" else eb) - 1
                        if i0 < 0 or not ev[i0][4]:
                            continue
                        x0, y0 = ev[i0][4], ev[i0][5]; qty = y0 - x0 * y0 / (x0 + s * (1 - f))
                        sl = lambda x, y: (x + s * (1 - f)) - (x + s * (1 - f)) * (y - qty) / (y - qty + qty * (1 - f))
                        if ex.startswith("h"):
                            xb = eb + math.ceil(int(ex[1:]) / bt)
                        else:
                            xb = eb + math.ceil(300 / bt); j = i0 + 1
                            while j < len(ev) and ev[j][0] < xb:
                                if ev[j][4] and sl(ev[j][4], ev[j][5]) >= s * (1 + int(ex[2:]) / 100):
                                    xb = ev[j][0] + 1; break
                                j += 1
                        i1 = bisect.bisect_right(bns, xb - 1) - 1
                        v = (sl(ev[i1][4], ev[i1][5]) if ev[i1][4] else 0.0) - s
                        rets.append(v / s); per_day[p["day"]] += v
                    if rets:
                        pos_sum = sum(r for r in rets if r > 0); top = sorted(rets, reverse=True)[:max(1, len(rets) // 10)]
                        cells.append(f"{ex} {st.mean(rets):+.0%}/{st.median(rets):+.0%}/{sum(r > 0 for r in rets) / len(rets):.0%}/{(sum(top) / pos_sum if pos_sum > 0 else 0):.0%}"
                                     f" days+{sum(v > 0 for v in per_day.values())}/{len(per_day)}")
                print(f"    K{K:<2d} {pos:5s} " + " | ".join(cells), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
