#!/usr/bin/env python3
"""tolmodel.py CHAIN CPDUMP DAY...: what the volume-bot line pulls on. Every outside buy (not the machine, not the launcher) in every pool of
the line, with: how many distinct outside wallets the pool has seen up to and including this one (the buyer's rank), the size of the buy, the
pool's age at the buy; and whether the pull followed within 5 s. Then one wallet (WALLET env) profiled the same way, and a late-entry copy:
our buy at the block after the machine's first buy (size STAKE), exit on a tripwire (an outside buy >= TRIP or an outside wallet beyond rank K)
or at a take-profit M against the launch price on x3 pools (M*0.65 on x5), cap at pool age CAP s; on every pool of the line (entry ages from ENTRIES env, default machine,5,10,20). Writes out/tolmodel_first.json.
Read-only (reads out/ only)."""
import os, sys, json, gzip, math, collections, statistics as st
from copysim import Pool, buy, sell
from seatlab import q

STAKE = float(os.environ.get("STAKE", "0.00009")); GAS = float(os.environ.get("GAS", "0.000006")); TRIP = float(os.environ.get("TRIP", "0.0001"))
CAP = float(os.environ.get("CAP", "420")); WALLET = os.environ.get("WALLET", "0xe74fcc81553c2b1102accdfaafa663418119098d")
SIZE = [("zero", lambda s: s == 0), ("<0.0001", lambda s: 0 < s < 0.0001), (">=0.0001", lambda s: s >= 0.0001)]
AGE = [("<=2s", lambda a: a <= 2), ("2-10s", lambda a: 2 < a <= 10), (">10s", lambda a: a > 10)]


def main(ch, cpf, days):
    here = os.path.dirname(os.path.abspath(__file__))
    CP = json.load(gzip.open(os.path.join(here, cpf), "rt"))
    tapes = {day: json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")) for day in days}
    per = collections.defaultdict(list)
    for day in days:
        for pid, cps in CP[day].items():
            seen = {}
            for e, cp in zip(tapes[day]["pools"][pid]["ev"], cps):
                if cp and e[2] > 0 and cp not in seen:
                    seen[cp] = e[2]
            for cp, s in seen.items():
                per[cp].append(s)
    machine = {cp for cp, v in per.items() if len(v) >= 3 and st.median(v) >= 0.001}
    outside = lambda cp, p: cp and cp not in machine and cp != p["frm"]
    rows = []
    for day in days:
        bt = tapes[day]["bt"]
        for pid, cps in CP[day].items():
            p = tapes[day]["pools"][pid]; ev = p["ev"]; wallets = []
            for e, cp in zip(ev, cps):
                if e[0] > p["pull"] or e[2] <= 0 or not outside(cp, p):
                    continue
                if cp not in wallets:
                    wallets.append(cp)
                rows.append({"day": day, "pool": pid, "who": cp, "rank": wallets.index(cp) + 1, "first": wallets[-1] == cp and sum(1 for r in rows if r["pool"] == pid and r["who"] == cp) == 0,
                             "size": e[2], "age": (e[0] - p["add"]) * bt, "to_pull": (p["pull"] - e[0]) * bt})
    first = [r for r in rows if r["first"]]
    json.dump(first, open(os.path.join(here, "out/tolmodel_first.json"), "w"))
    print(f"== every outside wallet's first buy on the line ({len(first)} in {len({r['pool'] for r in first})} pools): share followed by the pull within 5 s (n)")
    print("   rank = distinct outside wallets in the pool so far, this one included")
    print("   " + " " * 12 + "".join(f"{a:>26s}" for a, _ in AGE))
    for rk in (1, 2, 3, 4, 5):
        for sn, sf in SIZE:
            cells = []
            for an, af in AGE:
                rs = [r for r in first if (r["rank"] == rk if rk < 5 else r["rank"] >= 5) and sf(r["size"]) and af(r["age"])]
                cells.append(f"{sum(r['to_pull'] <= 5 for r in rs) / len(rs):4.0%} ({len(rs):4d})" if rs else " " * 11)
            if any(c.strip() for c in cells):
                print(f"   rank {rk if rk < 5 else '5+'} {sn:9s}" + "".join(f"{c:>26s}" for c in cells))
    w = [r for r in first if r["who"] == WALLET]
    if w:
        print(f"\n== {WALLET[:10]}: {len(w)} pools | buy {q([r['size'] for r in w])} | in at {q([r['age'] for r in w])} s | rank {dict(collections.Counter(r['rank'] for r in w))}"
              f"\n   pulled within 5 s {sum(r['to_pull'] <= 5 for r in w) / len(w):.0%} | pull after its buy {q([r['to_pull'] for r in w])} s")
        for rk in sorted({r["rank"] for r in w}):
            rs = [r for r in w if r["rank"] == rk]
            print(f"   as rank {rk}: {len(rs):4d} pools, pulled within 5 s {sum(r['to_pull'] <= 5 for r in rs) / len(rs):.0%}, within 60 s {sum(r['to_pull'] <= 60 for r in rs) / len(rs):.0%}")

    def run(k, m, entry):
        agg = collections.Counter(); pnl = 0.0; n = 0
        for day in days:
            bt = tapes[day]["bt"]
            for pid, cps in CP[day].items():
                p = tapes[day]["pools"][pid]; P = Pool(p, bt); ev = P.ev; f = p["fee"]; pull = p["pull"]
                if entry == "machine":
                    mb = next((i for i, (e, cp) in enumerate(zip(ev, cps)) if e[2] >= 0.01 and (cp in machine or cp == p["frm"])), None)
                    if mb is None:
                        continue
                    eblk = ev[mb][0] + 1; i0 = mb
                else:
                    eblk = p["add"] + math.ceil(entry / bt); i0 = P.end_of(eblk - 1)
                    if i0 < 0:
                        continue
                if eblk >= pull:                                   # already pulled: not a pool we would enter
                    continue
                n += 1
                st0 = P.state(P.end_of(eblk - 1))
                if not st0:
                    n -= 1; continue
                qty = buy(*st0, STAKE, f); st1 = P.state(0) or st0; price0 = st1[0] / st1[1]         # the take-profit is against the launch price
                tgt = m if round(p["nin"]) == 3 else m * 0.65
                cap = p["add"] + math.ceil(CAP / bt); wallets = {cp for e, cp in zip(ev[:i0 + 1], cps) if e[2] > 0 and outside(cp, p)}; xblk = None
                for i in range(i0 + 1, len(ev)):
                    e = ev[i]; cp = cps[i]
                    if e[0] >= pull or e[0] >= cap:
                        break
                    if e[0] < eblk:
                        continue
                    if e[2] > 0 and outside(cp, p):
                        new = cp not in wallets; wallets.add(cp)
                        if e[2] >= TRIP or (new and len(wallets) > k):
                            xblk = e[0] + 1; break
                    if e[4] and (e[4] / e[5]) / price0 >= tgt:
                        xblk = e[0] + 1; break
                if xblk is None:
                    xblk = cap
                if xblk >= pull:
                    agg["pulled"] += 1; v = -STAKE - GAS
                else:
                    v = sell(*P.state(P.end_of(xblk - 1)), qty, f) - STAKE - GAS; agg["win" if v > 0 else "loss"] += 1
                pnl += v
        return n, agg, pnl

    print(f"\n== late-entry copy at {STAKE:g} on every pool of the line (if tolerated): exit on tripwire (>= {TRIP:g} outside buy or a wallet beyond rank K) or take-profit")
    for entry in [x if x == "machine" else float(x) for x in os.environ.get("ENTRIES", "machine,5,10,20").split(",")]:
        for k, m in ((3, 6.5), (4, 6.5), (4, 7.5)):
            n, agg, pnl = run(k, m, entry)
            print(f"   entry {'after the first machine buy' if entry == 'machine' else f'at {entry} s':28s} K {k} tp {m}: pools {n:5d} won {agg['win']:5d} lost {agg['loss']:5d} pulled {agg['pulled']:5d} | pnl {pnl:+.4f}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
