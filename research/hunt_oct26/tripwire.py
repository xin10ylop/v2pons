#!/usr/bin/env python3
"""tripwire.py CHAIN CPDUMP ENTRIES DAY...: is the pull a reaction to something visible on chain in time to sell? And who are the outside
wallets whose arrival coincides with it? Same inputs as seatlab.py.

  1 early buyers  per day, the outside wallets (not the machine) buying in the first 2 s of a pool, how many pools each is in, and the pool's
                  fate when it is there; then pools by the count of early outside wallets, per day
  2 triggers      for the seat's never-sold entries: did an outside buy (size >= TRIP, or a new outside wallet beyond the first K) land in the
                  LEAD seconds before the pull? If so a sell fired on seeing it lands before the pull
  3 rules         copy at STAKE, entry +1; mirror; trip: sell at the block after an outside buy >= TRIP; wallets K: sell when a (K+1)th outside
                  wallet appears; both with mirror as the normal exit, and with a take-profit M on x3 pools (M*0.65 on x5) instead
Read-only (reads out/ only)."""
import os, sys, json, gzip, math, collections, statistics as st
from copysim import Pool, buy, sell
from seatlab import q

STAKE = float(os.environ.get("STAKE", "0.00009")); GAS = float(os.environ.get("GAS", "0.000006"))
TRIP = float(os.environ.get("TRIP", "0.0001")); LEAD = float(os.environ.get("LEAD", "5")); CAP = float(os.environ.get("CAP", "420"))


def main(ch, cpf, entf, days):
    here = os.path.dirname(os.path.abspath(__file__))
    CP = json.load(gzip.open(os.path.join(here, cpf), "rt"))
    ent = collections.defaultdict(dict)
    for x in json.load(open(os.path.join(here, entf))):
        ent[x["day"]][x["pool"]] = x
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

    print("== 1 early outside buyers (first 2 s of the pool), per day: wallet, pools, the pool pulled within 15 s when it is there")
    for day in days:
        bt = tapes[day]["bt"]; w = collections.defaultdict(list); cnt = collections.Counter()
        for pid, cps in CP[day].items():
            p = tapes[day]["pools"][pid]; ev = p["ev"]; life = (p["pull"] - p["add"]) * bt; early = set()
            for e, cp in zip(ev, cps):
                if e[2] > 0 and outside(cp, p) and (e[0] - p["add"]) * bt <= 2 and cp not in early:
                    early.add(cp); w[cp].append(life)
            cnt[len(early)] += 1
        top = sorted(w.items(), key=lambda kv: -len(kv[1]))[:6]
        print(f"   {day}: " + " | ".join(f"{cp[:10]} {len(v)}p {sum(l <= 15 for l in v) / len(v):.0%}" for cp, v in top))
        print(f"            pools by early outside wallets: {dict(sorted(cnt.items()))}")

    print(f"\n== 2 the seat's never-sold entries: what landed in the {LEAD:g} s before the pull")
    kinds = collections.Counter(); lead_t = []
    for day in days:
        bt = tapes[day]["bt"]
        for pid, x in ent[day].items():
            if x["s"] is not None:
                continue
            p = tapes[day]["pools"][pid]; ev = p["ev"]; cps = CP[day].get(pid)
            if not cps:
                continue
            b = ev[x["b"]]; wallets = set(); trig = None
            for e, cp in zip(ev, cps):
                if e[0] > p["pull"] or e[2] <= 0 or not outside(cp, p):
                    continue
                new = cp not in wallets; wallets.add(cp)
                if e[0] > b[0] and (p["pull"] - e[0]) * bt <= LEAD and (e[2] >= TRIP or (new and len(wallets) >= 4)):
                    trig = trig or (("stranger" if e[2] >= TRIP else "4th wallet"), (p["pull"] - e[0]) * bt)
            kinds[trig[0] if trig else "nothing visible"] += 1
            if trig:
                lead_t.append(trig[1])
    print(f"   {dict(kinds)} | when something did: pull came {q(lead_t)} s after it")

    def run(trip, k, m):
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
                sblk = ev[x["s"]][0] + 1 if x["s"] is not None else None
                tgt = (m if round(p["nin"]) == 3 else m * 0.65) if m else None
                cap = eblk + math.ceil(CAP / bt); wallets = set(); xblk = None
                for e, cp in zip(ev, cps):
                    if e[2] > 0 and outside(cp, p) and e[0] <= b[0]:
                        wallets.add(cp)
                for i in range(x["b"] + 1, len(ev)):
                    e = ev[i]; cp = cps[i]
                    if e[0] >= pull or e[0] >= cap:
                        break
                    if tgt is None and sblk and e[0] >= sblk - 1:
                        xblk = sblk; break
                    if e[2] > 0 and outside(cp, p):
                        new = cp not in wallets; wallets.add(cp)
                        if (trip and e[2] >= TRIP) or (k and new and len(wallets) > k):
                            xblk = e[0] + 1; break
                    if tgt and e[4] and (e[4] / e[5]) / price0 >= tgt:
                        xblk = e[0] + 1; break
                if xblk is None:
                    xblk = sblk if (tgt is None and sblk) else cap
                if xblk >= pull:
                    agg["pulled"] += 1; v = -STAKE - GAS
                else:
                    v = sell(*P.state(P.end_of(xblk - 1)), qty, f) - STAKE - GAS; agg["win" if v > 0 else "loss"] += 1
                pnl += v; per_day[day] += v
        return agg, pnl, per_day

    print(f"\n== 3 our copy at {STAKE:g}, entry +1, all {sum(len(v) for v in ent.values())} entries:")
    rules = [("mirror", (0, 0, 0)), ("mirror + trip", (1, 0, 0)), ("mirror + wallets 3", (0, 3, 0)), ("mirror + trip + wallets 3", (1, 3, 0))]
    rules += [(f"trip + wallets 3 + tp {m}", (1, 3, m)) for m in (4.4, 5.5, 6.5, 7.5)]
    for name, (t, k, m) in rules:
        agg, pnl, per_day = run(t, k, m)
        print(f"   {name:28s} won {agg['win']:5d} lost {agg['loss']:5d} pulled {agg['pulled']:5d} | pnl {pnl:+.4f} | per day "
              + " ".join(f"{d[4:]}:{v:+.3f}" for d, v in sorted(per_day.items())), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
