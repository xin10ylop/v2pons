#!/usr/bin/env python3
"""pumpreport.py OUTDIR [MIN_OOS] [STAGE_B_IDS]: pumpscan.py's wave.json as markdown (offline).

The ranked operator table (operators with MIN_OOS out-of-sample paper trades or more, default 3; ranked by the paper P&L at 0.5 SOL,
'end' entry), the pooled results, the launch classes (Mayhem mode, op-wallet wave, contested first seats), the wave rate in contested
vs uncontested launches, and clock stability by day. With STAGE_B_IDS (a file of operator ids picked after the screening), the paper
trades of those operators are also summed over the launches added after the pick only (pumpwave.py's second fetch), which were not
seen when they were picked."""
import json, sys, time, collections, statistics as st

d = json.load(open(sys.argv[1] + "/wave.json")); MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 3
stageB = set(x.strip() for x in open(sys.argv[3])) if len(sys.argv) > 3 else set()
first_seen = json.load(open(sys.argv[1] + "/stageA_mints.json")) if stageB else []
first_seen = set(first_seen)
med = lambda xs: st.median(xs) if xs else None
f = lambda x, n=2: "-" if x is None else f"{x:.{n}f}"
SZ = ("0.1", "0.5", "1.0")


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def tot(ls, kind, key):
    v = [l[kind].get(key) for l in ls if l[kind].get(key) is not None]
    return (sum(v), len(v), sum(1 for x in v if x > 0)) if v else (0.0, 0, 0)


def summary(o):
    L = o["launches"]; days = 3.0
    wave = [l for l in L if l["has_wave"]]; con = [l for l in L if l["contested"]]; unc = [l for l in L if not l["contested"]]
    clk = [l["clock_slot"] for l in L if l["clock_slot"] is not None]; clk_s = [l["clock_s"] for l in L if l["clock_s"] is not None]
    byday = collections.defaultdict(list)
    for l in L:
        if l["clock_slot"] is not None:
            byday[l["day"]].append(l["clock_slot"])
    daymed = {k: med(v) for k, v in sorted(byday.items())}
    oos = [l for l in L if l["prior_clock"] is not None]
    within = [abs(l["clock_slot"] - l["prior_clock"]) <= max(5, 0.25 * l["prior_clock"]) for l in oos if l["clock_slot"] is not None]
    return {"id": o["id"], "members": o["members"], "funders": o["funders"], "per_day": o["n_window"] / days, "n": len(L),
            "mayhem": sum(1 for l in L if l["mayhem"]) / len(L), "dev": med([l["dev_sol"] for l in L]),
            "bundle_n": med([l["bundle_n"] for l in L]), "bundle_op": med([l["bundle_op_sol"] for l in L]),
            "bundle_gen": med([l["bundle_generic_sol"] for l in L]),
            "wave_share": len(wave) / len(L), "wave_sol": med([l["wave_sol"] for l in wave]), "wave_s": med([l["wave_s"] for l in wave]),
            "wave_end_s": med([l["wave_end_s"] for l in wave]), "agent": med([l["agent_buy_sol"] for l in L if l["mayhem"]]),
            "clock": med(clk), "clock_p25": q(clk, 0.25), "clock_p75": q(clk, 0.75), "clock_s": med(clk_s), "n_clock": len(clk),
            "daymed": daymed, "hit": (sum(within) / len(within)) if within else None,
            "contested": len(con) / len(L), "wave_con": (sum(l["has_wave"] for l in con) / len(con)) if con else None,
            "wave_unc": (sum(l["has_wave"] for l in unc) / len(unc)) if unc else None, "n_con": len(con), "n_unc": len(unc),
            "paper": {s: tot(L, "paper", "end" + s) for s in SZ}, "paper_top": tot(L, "paper", "top0.5"),
            "paper25": tot(L, "paper25", "end0.5"),
            "hind": {s: tot(L, "hind", "end" + s) for s in SZ}, "s60": {s: tot(L, "s60", "end" + s) for s in SZ},
            "dump_first": (sum(1 for l in oos if l["dump_before_exit"]) / len(oos)) if oos else None,
            "lift": med([l["lift_peak"] for l in L if l["lift_peak"]]), "grad": sum(1 for l in L if l["graduated"]),
            "outsiders": med([l["outsiders"] for l in L]), "seat_n": med([l["seat_n"] for l in L]),
            "stageB": o["id"] in stageB,
            "paperB": {s: tot([l for l in L if l["mint"] not in first_seen], "paper", "end" + s) for s in SZ} if o["id"] in stageB else None}


S = [summary(o) for o in d["ops"]]
R = [s for s in S if s["paper"]["0.5"][1] >= MIN]
R.sort(key=lambda s: -s["paper"]["0.5"][0])
allL = [l for o in d["ops"] for l in o["launches"]]
print(f"# pump.fun wave operators: screening results\n")
print("Coverage: pumpcensus.py read every pump.fun creation of the 3 days to Oct 24 2026 12:00 UTC (142,942); pumpops.py found 2,540 creators "
      "with 5+ SOL-quoted launches (2,338 operators after merging creators that share a non-hub first funder). pumpwave.py read the first "
      "15 minutes of 6 launches (spread over the window) for the 277 largest operators (54+ launches each, 59% of all repeat-creator "
      "launches) before the Helius key ran out of credits; smaller operators are not covered. Not done for the same reason: the deeper "
      "15-launch sample of the picked operators (pumpselect.py) and the wallet funding lookups (pumpwave.py links), so operator wallets are "
      "the dev, the creation-slot bundle and wallets recurring across the operator's sampled launches, not funding-verified; generic = buys "
      "in sampled launches of 3+ operators. Out-of-sample paper trades need 2 earlier sampled launches, so at most 4 per operator.\n")
print(f"Fees used: pump.fun protocol + creator fee from the TradeEvents (1.25% a leg at launch: 0.95% + 0.30%; Mayhem agent trades 0%); "
      f"priority/tip per leg: entry {d['prio_in']:.6f} SOL (75th percentile of tx fee + Jito tip of first-seat buys; median "
      f"{d['first_cost_median']:.6f}), exit {d['prio_out']:.6f} SOL (median of all trades). Token-account rent (~0.002 SOL, refunded on close) left out.\n")
n = len(allL)
print(f"Launches analysed: {n} from {len(d['ops'])} operators; Mayhem mode {sum(1 for l in allL if l['mayhem'])} ({100 * sum(1 for l in allL if l['mayhem']) / n:.0f}%); "
      f"op-wallet wave (>= {d['wave_min']} SOL after the creation slot) {sum(l['has_wave'] for l in allL)} ({100 * sum(l['has_wave'] for l in allL) / n:.0f}%); "
      f"contested first seats {sum(l['contested'] for l in allL)} ({100 * sum(l['contested'] for l in allL) / n:.0f}%); graduated within 15 min {sum(l['graduated'] for l in allL)}.\n")
for name, sel in (("all", allL), ("Mayhem", [l for l in allL if l["mayhem"]]), ("not Mayhem", [l for l in allL if not l["mayhem"]])):
    con = [l for l in sel if l["contested"]]; unc = [l for l in sel if not l["contested"]]
    if sel:
        print(f"- {name}: wave rate contested {f(100 * sum(l['has_wave'] for l in con) / len(con), 0) if con else '-'}% of {len(con)}, "
              f"uncontested {f(100 * sum(l['has_wave'] for l in unc) / len(unc), 0) if unc else '-'}% of {len(unc)}")
po = {s: tot(allL, "paper", "end" + s) for s in SZ}; ph = {s: tot(allL, "hind", "end" + s) for s in SZ}; p6 = {s: tot(allL, "s60", "end" + s) for s in SZ}
print(f"\nPooled over every operator: out-of-sample paper " + ", ".join(f"{s} SOL {po[s][0]:+.2f} ({po[s][2]}/{po[s][1]} won)" for s in SZ)
      + "; hindsight " + ", ".join(f"{s} {ph[s][0]:+.2f}" for s in SZ) + "; sell at +60 s " + ", ".join(f"{s} {p6[s][0]:+.2f}" for s in SZ) + "\n")
pos = [s for s in R if s["paper"]["0.5"][0] > 0]
print(f"Operators with {MIN}+ out-of-sample trades: {len(R)}; positive at 0.5 SOL: {len(pos)}\n")
print("| # | creator(s) | funder | launches/day | sampled (Mayhem %) | dev buy SOL | bundle n / op SOL / sniper SOL | wave % / SOL / s (end +s) | agent buy SOL | "
      "clock slots median [p25-p75] (s) | clock by day | clock hit % | contested % | wave % contested / uncontested | paper OOS 0.1 / 0.5 / 1 SOL (won/n) | "
      "top-of-slot 0.5 | p25-clock exit 0.5 | hindsight 0.5 / 1 | +60 s 0.5 / 1 | dump before our exit % |")
print("|" + "---|" * 20)
for k, s in enumerate(R, 1):
    cr = ", ".join(f"`{m}`" for m in s["members"][:3]) + (f" +{len(s['members']) - 3}" if len(s["members"]) > 3 else "")
    fu = ", ".join(f"`{x}`" for x in s["funders"][:2]) or "-"
    p = s["paper"]
    print(f"| {k} | {cr} | {fu} | {s['per_day']:.0f} | {s['n']} ({100 * s['mayhem']:.0f}) | {f(s['dev'])} | {f(s['bundle_n'], 0)} / {f(s['bundle_op'])} / {f(s['bundle_gen'])} | "
          f"{100 * s['wave_share']:.0f} / {f(s['wave_sol'])} / {f(s['wave_s'], 0)} ({f(s['wave_end_s'], 0)}) | {f(s['agent'])} | "
          f"{f(s['clock'], 0)} [{f(s['clock_p25'], 0)}-{f(s['clock_p75'], 0)}] ({f(s['clock_s'], 0)}) | "
          f"{' '.join(f'{k2[3:]}:{f(v, 0)}' for k2, v in s['daymed'].items())} | {f(100 * s['hit'], 0) if s['hit'] is not None else '-'} | "
          f"{100 * s['contested']:.0f} | {f(100 * s['wave_con'], 0) if s['wave_con'] is not None else '-'} / {f(100 * s['wave_unc'], 0) if s['wave_unc'] is not None else '-'} | "
          f"{p['0.1'][0]:+.3f} / {p['0.5'][0]:+.3f} / {p['1.0'][0]:+.3f} ({p['0.5'][2]}/{p['0.5'][1]}) | {s['paper_top'][0]:+.3f} | {s['paper25'][0]:+.3f} | "
          f"{s['hind']['0.5'][0]:+.2f} / {s['hind']['1.0'][0]:+.2f} | {s['s60']['0.5'][0]:+.2f} / {s['s60']['1.0'][0]:+.2f} | "
          f"{f(100 * s['dump_first'], 0) if s['dump_first'] is not None else '-'} |")
if stageB:
    B = [s for s in S if s["stageB"]]
    print(f"\nStage B: {len(B)} operators picked after the screening; paper trades on launches added after the pick only:")
    tb = {sz: [sum(s["paperB"][sz][0] for s in B), sum(s["paperB"][sz][1] for s in B), sum(s["paperB"][sz][2] for s in B)] for sz in SZ}
    print("  " + ", ".join(f"{sz} SOL {tb[sz][0]:+.3f} ({tb[sz][2]}/{tb[sz][1]} won)" for sz in SZ))
    for s in sorted(B, key=lambda s: -s["paperB"]["0.5"][0]):
        pb = s["paperB"]
        print(f"  - `{s['id']}`: new launches {pb['0.5'][1]}: {pb['0.1'][0]:+.3f} / {pb['0.5'][0]:+.3f} / {pb['1.0'][0]:+.3f} ({pb['0.5'][2]} won)")
# ---- breakdowns
def cls_line(name, sel):
    out = [f"| {name} | {len(sel)} |"]
    for k in ("paper", "paper25", "hind", "s60"):
        v = [l[k].get("end0.5") for l in sel if l.get(k, {}).get("end0.5") is not None]
        out.append(f" {sum(v):+.2f} / {st.mean(v):+.4f} / {st.median(v):+.4f} / {100 * sum(1 for x in v if x > 0) / len(v):.0f}% (n {len(v)}) |" if v else " - |")
    return "".join(out)


def hitrate(sel):
    h = [abs(l["clock_slot"] - l["prior_clock"]) <= max(5, 0.25 * l["prior_clock"]) for l in sel if l["prior_clock"] is not None and l["clock_slot"] is not None]
    return f"{sum(h)}/{len(h)} ({100 * sum(h) / len(h):.0f}%)" if h else "-"


fitids = {s["id"] for s in S if s["mayhem"] < 0.5 and s["wave_share"] >= 0.5 and s["n_clock"] >= 4 and s["clock_p75"] is not None
          and s["clock_p75"] <= max(s["clock_p25"] + 10, 1.5 * s["clock_p25"])}
FL = [l for o in d["ops"] if o["id"] in fitids for l in o["launches"]]
M = [l for l in allL if l["mayhem"]]; NM = [l for l in allL if not l["mayhem"]]
print("\n## P&L at 0.5 SOL by launch class (sum / mean / median / won)\n")
print("| class | launches | paper OOS (median-clock exit) | paper OOS (p25-clock exit) | hindsight best exit | sell at +60 s |")
print("|---|---|---|---|---|---|")
for name, sel in (("all", allL), ("Mayhem mode", M), ("not Mayhem", NM), ("not Mayhem, wave (brief's definition)", [l for l in NM if l["has_wave"]]),
                  ("not Mayhem, wave (strict: dev/bundle only)", [l for l in NM if l["has_wave_strict"]]),
                  ("not Mayhem, contested", [l for l in NM if l["contested"]]), ("not Mayhem, uncontested", [l for l in NM if not l["contested"]]),
                  (f"model-fit operators ({len(fitids)})", FL), ("model-fit, contested", [l for l in FL if l["contested"]]),
                  ("model-fit, uncontested", [l for l in FL if not l["contested"]])):
    print(cls_line(name, sel))
print(f"\nClock hit (the launch's first big dump within max(5 slots, 25%) of the median of the operator's earlier launches): all {hitrate(allL)}, "
      f"Mayhem {hitrate(M)}, not Mayhem {hitrate(NM)}, model-fit operators {hitrate(FL)}.")
nd = st_ = 0
for o in d["ops"]:
    byday = collections.defaultdict(list)
    for l in o["launches"]:
        if l["clock_slot"] is not None:
            byday[l["day"]].append(l["clock_slot"])
    if len(byday) >= 2:
        allc = [x for v in byday.values() for x in v]; m = st.median(allc); nd += 1
        st_ += all(abs(st.median(v) - m) <= max(5, 0.25 * m) for v in byday.values())
print(f"Day-to-day: {st_} of {nd} operators with clocks on 2+ days keep every day's median clock within max(5 slots, 25%) of their overall median.")
for name, sel in (("not Mayhem", NM), ("model-fit", FL)):
    con = [l for l in sel if l["contested"]]; unc = [l for l in sel if not l["contested"]]
    print(f"Wave rate, {name}: contested {100 * sum(l['has_wave'] for l in con) / max(1, len(con)):.0f}% (strict {100 * sum(l['has_wave_strict'] for l in con) / max(1, len(con)):.0f}%) of {len(con)}; "
          f"uncontested {100 * sum(l['has_wave'] for l in unc) / max(1, len(unc)):.0f}% (strict {100 * sum(l['has_wave_strict'] for l in unc) / max(1, len(unc)):.0f}%) of {len(unc)}; "
          f"median peak lift before the dump over the bundle price: contested {med([l['lift_peak'] for l in con if l['lift_peak']]) or 0:.3f}, "
          f"uncontested {med([l['lift_peak'] for l in unc if l['lift_peak']]) or 0:.3f}")
print(f"\n## Model-fit operators (not Mayhem, wave in half or more of the launches, clock p75 <= max(p25 + 10, 1.5 x p25)): {len(fitids)}\n")
for s in sorted([s for s in S if s["id"] in fitids], key=lambda s: -s["paper"]["0.5"][0]):
    print(f"- `{s['id']}` (funder `{(s['funders'] or ['-'])[0]}`): {s['per_day']:.0f}/day, dev {f(s['dev'])} SOL, bundle {f(s['bundle_n'], 0)} wallets {f(s['bundle_op'])} SOL, "
          f"wave {100 * s['wave_share']:.0f}% {f(s['wave_sol'])} SOL, clock {f(s['clock'], 0)} slots [{f(s['clock_p25'], 0)}-{f(s['clock_p75'], 0)}], by day "
          f"{' '.join(f'{k[3:]}:{f(v, 0)}' for k, v in s['daymed'].items())}, hit {f(100 * s['hit'], 0) if s['hit'] is not None else '-'}%, contested {100 * s['contested']:.0f}%, "
          f"paper 0.1/0.5/1 {s['paper']['0.1'][0]:+.3f}/{s['paper']['0.5'][0]:+.3f}/{s['paper']['1.0'][0]:+.3f} ({s['paper']['0.5'][2]}/{s['paper']['0.5'][1]}), "
          f"hindsight 0.5 {s['hind']['0.5'][0]:+.2f}, +60 s {s['s60']['0.5'][0]:+.2f}")
# ---- persistence: does an operator's out-of-sample P&L in its first two trades predict its next two?
def persist(group):
    a, b, ids = [], [], []
    for o in group:
        v = [l["paper"].get("end0.5") for l in o["launches"] if l["paper"].get("end0.5") is not None]
        if len(v) >= 4:
            a.append(sum(v[:2])); b.append(sum(v[2:4])); ids.append(o["id"])
    n = len(a)
    if n < 5:
        return n, None, [], 0
    rk = lambda x: {i: k for k, i in enumerate(sorted(range(n), key=lambda i: x[i]))}
    ra, rb = rk(a), rk(b)
    rho = 1 - 6 * sum((ra[i] - rb[i]) ** 2 for i in range(n)) / (n * (n * n - 1))
    both = [ids[i] for i in range(n) if a[i] > 0 and b[i] > 0]
    exp = sum(1 for x in a if x > 0) * sum(1 for y in b if y > 0) / n
    return n, rho, both, exp


mayops = [o for o in d["ops"] if o["launches"] and sum(l["mayhem"] for l in o["launches"]) / len(o["launches"]) >= 0.5]
nonops = [o for o in d["ops"] if o["launches"] and sum(l["mayhem"] for l in o["launches"]) / len(o["launches"]) < 0.5]
print("\n## Persistence of out-of-sample P&L (0.5 SOL): first two trades vs the next two, per operator\n")
for name, g in (("Mayhem-mode operators", mayops), ("other operators", nonops)):
    n, rho, both, exp = persist(g)
    print(f"- {name}: {n} operators with 4 trades; Spearman {rho:+.3f}; positive in both halves {len(both)} (expected if independent {exp:.1f})")
n, rho, both, exp = persist(mayops)
SS = {s["id"]: s for s in S}
print("\nMayhem-mode operators positive in both halves (leads for a deeper sample; 4 trades each, not validated):\n")
for i in sorted(both, key=lambda i: -SS[i]["paper"]["0.5"][0]):
    s = SS[i]
    print(f"- `{i}` (funder `{(s['funders'] or ['-'])[0]}`): {s['per_day']:.0f}/day, dev {f(s['dev'])} SOL, agent buys {f(s['agent'])} SOL (median), clock {f(s['clock'], 0)} slots "
          f"[{f(s['clock_p25'], 0)}-{f(s['clock_p75'], 0)}], hit {f(100 * s['hit'], 0) if s['hit'] is not None else '-'}%, paper 0.1/0.5/1 "
          f"{s['paper']['0.1'][0]:+.3f}/{s['paper']['0.5'][0]:+.3f}/{s['paper']['1.0'][0]:+.3f} ({s['paper']['0.5'][2]}/{s['paper']['0.5'][1]}), hindsight 0.5 {s['hind']['0.5'][0]:+.2f}, +60 s {s['s60']['0.5'][0]:+.2f}")
json.dump(S, open(sys.argv[1] + "/report_rows.json", "w"))
