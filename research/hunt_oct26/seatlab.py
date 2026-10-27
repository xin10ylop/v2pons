#!/usr/bin/env python3
"""seatlab.py CHAIN CPDUMP ENTRIES DAY...: the dust seat on a volume-bot line, dissected. Needs tape.py's tapes, cpdump.py's counterparties
for the line (CPDUMP, a file in this folder) and entries.py's entries for the seat wallet (ENTRIES).

Wallets on the line: the launcher (the pool's add transaction sender), the machine (counterparties buying 0.001+ in MACHINE_POOLS or more
line pools), dust (every other buyer whose first buy is under DUST) and strangers (the rest).

  1 machine   who the machine is, its buy cadence after the seat's entry, and the gap between its last swap and the pull (a tell?)
  2 losses    the seat's never-sold entries split into dead pools (no machine buy before the pull) and mid-pump pulls
  3 rules     our copy at STAKE (end of the seat's buy block), exit by rule, on every entry:
                mirror           sell when the seat sells (lost if it never does)
                dead T           sell at T s if no machine buy has come by then, else mirror
                dead T pause G   as above, and sell when the machine has been quiet for G s before the seat's sell
                dead T tp M      as dead T, but hold past the seat's sell for a price multiple M (x3 pools; M*0.65 on x5), guarded by
                                 the pause rule and a hard cap CAP s after entry
  4 dust      cumulative dust in a pool against how soon it was pulled: the ceiling for adding our buy next to the seat's
Read-only (reads out/ only)."""
import os, sys, json, gzip, bisect, math, collections, statistics as st
from copysim import Pool, buy, sell

STAKE = float(os.environ.get("STAKE", "0.00009")); GAS = float(os.environ.get("GAS", "0.000006"))
DUST = float(os.environ.get("DUST", "0.0001")); MACHINE_POOLS = int(os.environ.get("MACHINE_POOLS", "3")); CAP = float(os.environ.get("CAP", "420"))


def q(v, ps=(5, 25, 50, 75, 95)):
    if len(v) < 20:
        return f"n={len(v)}" + (f" median {st.median(v):.2f}" if v else "")
    k = st.quantiles(v, n=20)
    return " ".join(f"p{p}:{k[p // 5 - 1]:.2f}" for p in ps)


def main(ch, cpf, entf, days):
    here = os.path.dirname(os.path.abspath(__file__))
    CP = json.load(gzip.open(os.path.join(here, cpf), "rt"))
    ent = collections.defaultdict(dict)
    for x in json.load(open(os.path.join(here, entf))):
        ent[x["day"]][x["pool"]] = x
    tapes = {day: json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")) for day in days}
    # --- who is the machine
    per = collections.defaultdict(list)
    for day in days:
        for pid, cps in CP[day].items():
            ev = tapes[day]["pools"][pid]["ev"]; seen = {}
            for e, cp in zip(ev, cps):
                if cp and e[2] > 0 and cp not in seen:
                    seen[cp] = e[2]
            for cp, s in seen.items():
                per[cp].append(s)
    machine = {cp for cp, v in per.items() if len(v) >= MACHINE_POOLS and st.median(v) >= 0.001}
    print(f"== 1 machine: {len(machine)} wallets buy 0.001+ in {MACHINE_POOLS}+ pools; the largest:")
    for cp in sorted(machine, key=lambda c: -len(per[c]))[:6]:
        print(f"   {cp} pools {len(per[cp]):5d} first buy median {st.median(per[cp]):.4f}")
    gap, msell, cad = [], 0, []
    for day in days:
        bt = tapes[day]["bt"]
        for pid, cps in CP[day].items():
            p = tapes[day]["pools"][pid]; ev = p["ev"]
            m = [(e, cp) for e, cp in zip(ev, cps) if cp in machine or cp == p["frm"]]
            if m:
                gap.append((p["pull"] - m[-1][0][0]) * bt)
                msell += any(e[2] < 0 for e, _ in m[-3:])
                bb = [e[0] for e, _ in m if e[2] > 0]
                cad += [(b2 - b1) * bt for b1, b2 in zip(bb, bb[1:])]
    print(f"   machine buy cadence (s between its buys) {q(cad)}")
    print(f"   last machine swap -> pull (s) {q(gap)} | gap >= 5s in {sum(g >= 5 for g in gap) / len(gap):.0%}, >= 10s {sum(g >= 10 for g in gap) / len(gap):.0%}"
          f" | a machine sell among the last 3 machine swaps: {msell / len(gap):.0%} of pools")
    # --- the seat's losses
    dead = collections.Counter(); mid = collections.Counter(); dead_pull = []; mid_pull = []; mid_peak = []
    for day in days:
        bt = tapes[day]["bt"]
        for pid, x in ent[day].items():
            if x["s"] is not None:
                continue
            p = tapes[day]["pools"][pid]; ev = p["ev"]; cps = CP[day].get(pid)
            if not cps:
                continue
            b = ev[x["b"]]; n = round(p["nin"])
            mb = [e for e, cp in zip(ev, cps) if e[2] >= 0.01 and (cp in machine or cp == p["frm"]) and e[0] > b[0] and e[0] < p["pull"]]
            if not mb:
                dead[n] += 1; dead_pull.append((p["pull"] - b[0]) * bt)
            else:
                mid[n] += 1; mid_pull.append((p["pull"] - b[0]) * bt)
                mid_peak.append(max((e[4] / e[5]) / (b[4] / b[5]) for e in ev[x["b"]:] if e[0] < p["pull"] and e[4]))
    print(f"\n== 2 the seat's never-sold entries: dead pools (no machine buy at all) {dict(dead)} | pulled mid-pump {dict(mid)}")
    print(f"   dead: pull after the seat's entry (s) {q(dead_pull)} | pulled within 2s {sum(v <= 2 for v in dead_pull) / len(dead_pull):.0%}, 4s {sum(v <= 4 for v in dead_pull) / len(dead_pull):.0%}, 8s {sum(v <= 8 for v in dead_pull) / len(dead_pull):.0%}")
    print(f"   mid-pump: pull after entry (s) {q(mid_pull)} | peak multiple reached {q(mid_peak)}")

    # --- rules
    def run(rule):
        T, G, M = rule
        agg = collections.Counter(); pnl = 0.0; per_day = collections.defaultdict(float)
        for day in days:
            bt = tapes[day]["bt"]
            for pid, x in ent[day].items():
                p = tapes[day]["pools"][pid]; cps = CP[day].get(pid)
                if not cps:
                    continue
                P = Pool(p, bt); ev = P.ev; f = p["fee"]; pull = p["pull"]; b = ev[x["b"]]; eblk = b[0] + 1
                if eblk >= pull:
                    agg["pulled"] += 1; pnl -= STAKE + GAS; per_day[day] -= STAKE + GAS; continue
                st0 = P.state(P.end_of(b[0])); qty = buy(*st0, STAKE, f); price0 = st0[0] / st0[1]
                mach = [e for e, cp in zip(ev, cps) if (cp in machine or cp == p["frm"]) and e[0] > b[0]]
                mbuy = [e for e in mach if e[2] >= 0.01]
                sblk = ev[x["s"]][0] + 1 if x["s"] is not None else None       # mirror: the block after the seat's sell
                xblk = None
                if T and (not mbuy or (mbuy[0][0] - b[0]) * bt > T):
                    xblk = eblk + math.ceil(T / bt)
                else:
                    tgt = (M if round(p["nin"]) == 3 else M * 0.65) if M else None
                    cap = eblk + math.ceil(CAP / bt)
                    last = mbuy[0][0] if mbuy else b[0]
                    k = P.end_of(b[0]) + 1
                    while k < len(ev) and ev[k][0] < pull and ev[k][0] < cap:
                        e = ev[k]
                        if G and (e[0] - last) * bt > G:                       # the machine went quiet before this swap
                            xblk = last + math.ceil(G / bt); break
                        if tgt is None and sblk and e[0] >= sblk - 1:          # no tp: mirror
                            xblk = sblk; break
                        if tgt and e[4] and (e[4] / e[5]) / price0 >= tgt:
                            xblk = e[0] + 1; break
                        if any(m is e for m in mach):
                            last = e[0]
                        k += 1
                    if xblk is None:
                        if tgt is None and sblk:
                            xblk = sblk
                        elif G and (min(pull, cap) - last) * bt > G:
                            xblk = last + math.ceil(G / bt)
                        else:
                            xblk = cap if tgt else (sblk or cap)
                if xblk >= pull:
                    agg["pulled"] += 1; v = -STAKE - GAS
                else:
                    v = sell(*P.state(P.end_of(xblk - 1)), qty, f) - STAKE - GAS; agg["win" if v > 0 else "loss"] += 1
                pnl += v; per_day[day] += v
        return agg, pnl, per_day

    print(f"\n== 3 our copy at {STAKE:g}, entry +1, every entry of the seat ({sum(len(v) for v in ent.values())}), exit by rule:")
    rules = [("mirror", (0, 0, 0))] + [(f"dead {t}", (t, 0, 0)) for t in (2, 3, 4, 6)] + [(f"dead 4 pause {g}", (4, g, 0)) for g in (10, 20, 30)]
    rules += [(f"dead 4 pause {g} tp {m}", (4, g, m)) for g in (20, 30) for m in (4.4, 5.5, 6.5)]
    res = {}
    for name, rule in rules:
        agg, pnl, per_day = run(rule); res[name] = {"pnl": pnl, **agg, "per_day": dict(per_day)}
        print(f"   {name:24s} won {agg['win']:5d} lost {agg['loss']:5d} pulled {agg['pulled']:5d} | pnl {pnl:+.4f} | per day "
              + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(per_day.items())), flush=True)
    # --- dust ceiling
    rows = []
    for day in days:
        bt = tapes[day]["bt"]
        for pid, cps in CP[day].items():
            p = tapes[day]["pools"][pid]; ev = p["ev"]; first = {}
            for e, cp in zip(ev, cps):
                if cp and e[2] > 0 and cp not in machine and cp != p["frm"] and cp not in first and e[0] <= p["pull"]:
                    first[cp] = (e[2], (e[0] - p["add"]) * bt)
            dust = {cp: v for cp, v in first.items() if v[0] < DUST}; strange = {cp: v for cp, v in first.items() if v[0] >= DUST}
            early = [v for v in dust.values() if v[1] <= 2]
            rows.append({"life": (p["pull"] - p["add"]) * bt, "n_dust": len(dust), "dust_sum": sum(v[0] for v in dust.values()),
                         "early_n": len(early), "early_sum": sum(v[0] for v in early), "stranger": bool(strange), "n": round(p["nin"])})
    print(f"\n== 4 dust in the line's {len(rows)} pools (buyers under {DUST:g} that are not the machine); early = in the first 2 s:")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 99)):
        rs = [r for r in rows if lo <= r["early_n"] < hi and not r["stranger"]]
        if rs:
            print(f"   {lo}-{hi - 1 if hi < 99 else '+'} early dust buyers, no stranger: pools {len(rs):4d} | early dust sum median {st.median(r['early_sum'] for r in rs):.5f} max {max(r['early_sum'] for r in rs):.5f}"
                  f" | pulled within 15s {sum(r['life'] <= 15 for r in rs) / len(rs):.0%} | life median {st.median(r['life'] for r in rs):.0f}s")
    rs = [r for r in rows if r["stranger"]]
    print(f"   pools with a {DUST:g}+ outside buy: {len(rs)} | pulled within 15s {sum(r['life'] <= 15 for r in rs) / len(rs):.0%} | life median {st.median(r['life'] for r in rs):.0f}s")
    alive = [r for r in rows if r["life"] > 120]
    print(f"   pools alive 120s+: {len(alive)} | total dust taken in, median {st.median(r['dust_sum'] for r in alive):.5f} p95 {st.quantiles([r['dust_sum'] for r in alive], n=20)[18]:.5f} max {max(r['dust_sum'] for r in alive):.5f}")
    json.dump(res, open(os.path.join(here, "out/seatlab_rules.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
