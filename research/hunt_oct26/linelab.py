#!/usr/bin/env python3
"""linelab.py DAY...: three Robinhood lines found in the Nov 2 sweep, tested on their tapes (out/sel_rh_DAY.json from the census, filtered;
out/seltape_rh_DAY.json.gz from tape.py):

  opA     operator A, launched through 0x3194e326 (random fee and size per pool)
  hook11  the 11 ETH line with a per-pool hook that takes 10% of every swap (1,000 / 10,000 in beforeSwap and afterSwap)
  fee1x4  4 ETH, fee 0.0001%, tick spacing 1 (Oct 31 - Nov 1)

Every swap's sender is resolved (cached in out/who_rh.json). Per line:
  wallets    the launcher; the fleet (wallets buying in RECUR (default 3) or more of the line's pools); outsiders (everyone else)
  outsiders  each outsider's first buy per pool: size, pool age; pulled within 5 / 30 s of it (against the line's base rate: the share of
             its pools alive at that age that were pulled within the next 5 s); sold before the pull; profit
  seat       paper trades on the recorded reserves, our buy STAKE (env, default 0.01) at the pool's fee, and for hook11 10% off each leg:
             entry at the block after the add (front), the block after the fleet's first buy, or at a pool age of 10 / 30 / 60 s;
             exit after HOLD 15 / 60 / 180 s or at a take-profit of +20 / +50% (else at 180 s); the pull first = -100%
The paper seat does not model a reaction to our own buy: the outsider rows are that test. Read-only (out/ and the cache), public RPCs."""
import os, sys, json, gzip, math, bisect, collections, statistics as st
import hlib as H
from copysim import buy, sell

OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
STAKE = float(os.environ.get("STAKE", "0.01")); RECUR = int(os.environ.get("RECUR", "3")); GAS = 0.000006
TAX = {"hook11": 0.10}


def kind_of(p, hooked):
    if p.get("to") == OPA:
        return "opA"
    if p["id"] in hooked:
        return "hook11"
    if p["venue"] == "v4" and p["fee"] == 1 and p["ts"] == 1 and round(p.get("nat_in") or 0, 2) == 4:
        return "fee1x4"


def main(days):
    here = os.path.dirname(os.path.abspath(__file__))
    hooked = {x["pool"] for x in json.load(open(os.path.join(here, "out/bc_deep_rh.json"))) if x["size"] == 7196}
    pools = {}; bt = None
    for d in days:
        cen = {p["id"]: p for p in json.load(open(os.path.join(here, f"out/sel_rh_{d}.json")))["chains"]["rh"]["rugs"]}
        t = json.load(gzip.open(os.path.join(here, f"out/seltape_rh_{d}.json.gz"), "rt")); bt = t["bt"]
        for pid, p in t["pools"].items():
            k = kind_of(cen[pid], hooked) if pid in cen else None
            if k and p["ev"]:
                pools[pid] = dict(p, kind=k, day=d)
    cache_p = os.path.join(here, "out/who_rh.json")
    try:
        cache = json.load(open(cache_p))
    except (OSError, ValueError):
        cache = {}
    todo = sorted({e[6] for p in pools.values() for e in p["ev"]} - set(cache))
    got = H.batch(H.CH["rh"]["rpc"], [("eth_getTransactionByHash", [h]) for h in todo], size=50, workers=4, tries=10)
    for h, x in zip(todo, got):
        if x:
            cache[h] = [x["from"].lower(), (x.get("to") or "").lower()]
    json.dump(cache, open(cache_p, "w"))
    who = lambda e: (cache.get(e[6]) or [None])[0]
    for kind in ("opA", "hook11", "fee1x4"):
        P = [p for p in pools.values() if p["kind"] == kind]
        if not P:
            continue
        seen = collections.Counter()
        for p in P:
            for w in {who(e) for e in p["ev"] if e[2] > 0}:
                seen[w] += 1
        fleet = {w for w, c in seen.items() if c >= RECUR and w}
        lives = sorted((p["pull"] - p["add"]) * bt for p in P)
        print(f"\n== {kind}: {len(P)} pulled pools over {len({p['day'] for p in P})} days | launch native median {st.median(p['nin'] or 0 for p in P):.2f} | "
              f"life median {st.median(lives):.0f}s | fleet wallets {len(fleet)} (in {RECUR}+ pools)")

        def base(age, win=5):
            alive = len(lives) - bisect.bisect_right(lives, age)
            return (bisect.bisect_right(lives, age + win) - bisect.bisect_right(lives, age)) / alive if alive else 0.0
        rows = []
        for p in P:
            flows = collections.defaultdict(lambda: [None, 0.0, 0.0])
            for e in p["ev"]:
                w = who(e)
                if not w or w == p["frm"] or w in fleet or e[0] > p["pull"]:
                    continue
                f = flows[w]
                if e[2] > 0:
                    f[1] += e[2]
                    if f[0] is None:
                        f[0] = e
                else:
                    f[2] += -e[2]
            for w, (e0, bought, sold) in flows.items():
                if e0 is None:
                    continue
                age = (e0[0] - p["add"]) * bt; dt = (p["pull"] - e0[0]) * bt
                rows.append({"size": e0[2], "age": age, "dt": dt, "out": sold > 0, "pnl": sold - bought, "base": base(age)})
        for name, sel in (("dust < 0.0002", lambda r: r["size"] < 0.0002), ("real >= 0.0002", lambda r: r["size"] >= 0.0002)):
            rs = [r for r in rows if sel(r)]
            if rs:
                print(f"   outsiders, {name}: {len(rs)} buys | pulled within 5s {sum(r['dt'] <= 5 for r in rs) / len(rs):.0%} (base rate {sum(r['base'] for r in rs) / len(rs):.0%}),"
                      f" within 30s {sum(r['dt'] <= 30 for r in rs) / len(rs):.0%} | sold before the pull {sum(r['out'] for r in rs) / len(rs):.0%}"
                      f" | net {sum(r['pnl'] for r in rs):+.4f} on {sum(r['size'] for r in rs):.4f} | size median {st.median(r['size'] for r in rs):.4f}, in at median {st.median(r['age'] for r in rs):.0f}s")
            else:
                print(f"   outsiders, {name}: none")
        # paper seat
        tax = TAX.get(kind, 0.0)
        res = collections.defaultdict(lambda: [0, 0, 0, 0.0])                       # rule -> n, won, pulled, pnl
        for p in P:
            ev = p["ev"]; bns = [e[0] for e in ev]; f = p["fee"]; pull = p["pull"]
            fb = next((e[0] for e in ev if e[2] > 0 and who(e) in fleet), None)
            entries = {"front": p["add"] + 1, "fleet1+1": fb + 1 if fb else None}
            entries.update({f"age{a}": p["add"] + math.ceil(a / bt) for a in (10, 30, 60)})
            for en, eb in entries.items():
                if eb is None:
                    continue
                k0 = bisect.bisect_right(bns, eb - 1) - 1
                if eb >= pull:
                    continue                                                          # gone before we could enter: not a trade
                st0 = (ev[k0][4], ev[k0][5]) if k0 >= 0 and ev[k0][4] else None
                if not st0:
                    continue
                q = buy(*st0, STAKE * (1 - tax), f)
                for ex in ("hold15", "hold60", "hold180", "tp20", "tp50"):
                    if ex.startswith("hold"):
                        xb = eb + math.ceil(int(ex[4:]) / bt)
                    else:
                        x = 1 + int(ex[2:]) / 100; xb = eb + math.ceil(180 / bt); k = k0 + 1
                        while k < len(ev) and ev[k][0] < min(pull, xb):
                            if ev[k][4] and sell(ev[k][4], ev[k][5], q, f) * (1 - tax) >= STAKE * x:
                                xb = ev[k][0] + 1; break
                            k += 1
                    r = res[(en, ex)]; r[0] += 1
                    if xb >= pull:
                        r[2] += 1; r[3] -= STAKE + GAS; continue
                    k1 = bisect.bisect_right(bns, xb - 1) - 1
                    v = sell(ev[k1][4], ev[k1][5], q, f) * (1 - tax) - STAKE - GAS
                    r[1] += v > 0; r[3] += v
        print(f"   paper seat at {STAKE:g} (no reaction to our buy; tax {tax:.0%} a leg):")
        for en in ("front", "fleet1+1", "age10", "age30", "age60"):
            print("     " + f"{en:9s}" + " | ".join(f"{ex} {res[(en, ex)][3]:+.4f} ({res[(en, ex)][1]}/{res[(en, ex)][0]} won, {res[(en, ex)][2]} pulled)"
                                              for ex in ("hold15", "hold60", "hold180", "tp20", "tp50") if res[(en, ex)][0]))


if __name__ == "__main__":
    main(sys.argv[1:])
