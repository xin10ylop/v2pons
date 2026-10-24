#!/usr/bin/env python3
"""dammscan.py OUTDIR: the seat test on dammseat.py's DAMM v2 sample (offline; reads OUTDIR and out/amm/damm7*.json).

Pool model: constant product on the two vaults' balances (checked: the sample's pools are full range, and each observed swap's output
is compared with the constant-product output to get its implied fee). Events per transaction (sorted by slot, then signature order):
creation (the deposit), swap (buy: SOL into the vault; sell: SOL out), add, the pull (RemoveLiquidity / RemoveAllLiquidity taking SOL
out), no-op. The trader is the fee payer.
Wallet classes (over the whole sample):
  network  the creators of the 80+ SOL lines and the relays between them (dammchain.py)
  fleet    the operator's: first funder (dammseat.py wallets) in the network or in the fleet, SOL received from the network inside
           the sampled transactions, or a newest transaction paid or co-signed by the network (dammseat.py control; the network here
           includes the two controller wallets that sweep the buyers and clean up the creators, out/amm/seat/controllers.json), or
           co-signed or funded by a controller or creator in its swept transactions (dammseat.py sweep: one controller's newest 2000,
           three creators' newest 1000 each)
  recur    trades in 2+ sampled pools of the same line, not funded by the network, and in fewer than 3 lines
  bot      trades in 3+ lines (cross-line), not funded by the network
  out      the rest; 'verified' when its first funder was looked up and is not linked
The brief's fleet = fleet + recur (+ bot, which also recurs within lines; reported apart).
Per pool: buy and sell SOL by class; the SOL left at the pull (vault SOL before the pull minus the deposit) split by class (net SOL
in = buys - sells); the fleet's first buy (fleet or recur), its first burst (fleet buys with gaps of 10 slots or less); pre-fleet
outsider buys and what followed (the fleet came, the pull's timing); the pull's timing against outsider buys (pools whose pull lands
within 2 slots after an outsider buy >= 0.1 SOL, against the chance of that for a pull slot drawn at random over the pool's life).
Paper seat (0.5 / 1 / 2 SOL): buy at the end of slot c+1 ('top' variant: before the trades of slot c+1), others replayed with our
impact, sell: 'burst' = 10 slots after the last buy of the first fleet burst after our entry, where the fleet is only what is known
live (wallets that bought 0.01+ SOL in the line's earlier sampled pools; none for a line's first pool), or the delay below when no
such buy comes; 'delay' = a fixed delay, the median of the line's earlier pools' first-burst end (s after creation); -100% when the pull comes
first. Benchmarks: the best exit before the
pull (hindsight) and +60 s. Fee per leg: the pool's base fee (Pool account) or the implied fee of the swaps around, whichever is
higher; priority cost per leg: entry = p75, exit = median of (tx fee + Jito tip) of the swaps in slots c..c+2.
Verdict (linescan.py's rule): OPEN with 2+ pre-fleet outsider cases holding >= 0.1 SOL into the fleet's first buy where the fleet still
came and the pull was not early, and none against; CLOSED with 2+ against (the fleet skipped and pulled, or the pull came within
120 s of the outsider's buy or before 0.8x the line's earliest clean pull) outnumbering the for; NO PUMP when the fleet buys in fewer
than half the pools or the median pump is under 1.3; else UNKNOWN. Writes OUTDIR/scan.json and OUTDIR/seatreport.md."""
import json, os, sys, time, collections, statistics as st

JITO = {"96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe", "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
        "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49", "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
        "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"}
SIZES = (0.5, 1.0, 2.0)
med = lambda xs: st.median(xs) if xs else None


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def events(T, p):
    ev = []
    rows = sorted(T["rows"], key=lambda r: (r["slot"], r["i"]))
    for r in rows:
        ix = set(r["ix"]); sd, td = r["sol_d"], r["tok_d"]
        if ix & {"InitializeCustomizablePool", "InitializePool"} and sd > 0 and td > 0:
            k = "create"
        elif ix & {"RemoveLiquidity", "RemoveAllLiquidity"} and sd < 0:
            k = "pull"
        elif ix & {"AddLiquidity"} and sd > 0 and td > 0:
            k = "add"
        elif sd > 0 and td < 0:
            k = "buy"
        elif sd < 0 and td > 0:
            k = "sell"
        else:
            k = "none"
        tip = sum(l for f, t_, l in r["sys"] if t_ in JITO)
        ev.append({"k": k, "w": r["payer"], "slot": r["slot"], "t": r["t"], "sd": sd, "td": td, "cost": r["fee"] + tip, "sys": r["sys"], "sig": r["sig"]})
    S = T_ = 0
    for e in ev:                                                    # reserves after each event
        e["S0"], e["T0"] = S, T_
        S += e["sd"]; T_ += e["td"]
        e["S"], e["T"] = S, T_
    return ev


def implied_fees(ev):
    out = []
    for e in ev:
        if e["k"] in ("buy", "sell") and e["S0"] > 0 and e["T0"] > 0:
            if e["k"] == "buy":
                cp = e["T0"] * e["sd"] / (e["S0"] + e["sd"]); got = -e["td"]
            else:
                cp = e["S0"] * e["td"] / (e["T0"] + e["td"]); got = -e["sd"]
            if cp > 1000:
                out.append((e["t"], 1 - got / cp))
    return out


def replay(ev, i0, x_lam, exit_i, fee):
    """buy x before ev[i0]; replay to ev[exit_i] inclusive; sell; SOL back (lamports) or 0 if the pull comes first"""
    S, T = (ev[i0 - 1]["S"], ev[i0 - 1]["T"]) if i0 > 0 else (0, 0)
    if S <= 0 or T <= 0:
        return None
    net = x_lam * (1 - fee); q = T * net / (S + net); S += x_lam; T -= q
    for e in ev[i0:exit_i + 1]:
        if e["k"] == "pull":
            return 0.0
        if e["k"] == "buy":
            o = T * e["sd"] * (1 - fee) / (S + e["sd"] * (1 - fee)); S += e["sd"]; T -= o
        elif e["k"] == "sell":
            o = S * e["td"] * (1 - fee) / (T + e["td"] * (1 - fee)); S -= o; T += e["td"]
        elif e["k"] == "add" and e["S0"] > 0:
            f = e["S"] / e["S0"]; S *= f; T *= f
    return S * q * (1 - fee) / (T + q * (1 - fee))


def value_path(ev, i0, x_lam, fee, t_end):
    S, T = (ev[i0 - 1]["S"], ev[i0 - 1]["T"]) if i0 > 0 else (0, 0)
    if S <= 0 or T <= 0:
        return []
    net = x_lam * (1 - fee); q = T * net / (S + net); S += x_lam; T -= q
    out = [(i0 - 1, S * q * (1 - fee) / (T + q * (1 - fee)))]
    for i in range(i0, len(ev)):
        e = ev[i]
        if e["k"] == "pull" or e["t"] > t_end:
            break
        if e["k"] == "buy":
            o = T * e["sd"] * (1 - fee) / (S + e["sd"] * (1 - fee)); S += e["sd"]; T -= o
        elif e["k"] == "sell":
            o = S * e["td"] * (1 - fee) / (T + e["td"] * (1 - fee)); S -= o; T += e["td"]
        out.append((i, S * q * (1 - fee) / (T + q * (1 - fee))))
    return out


def main(outdir):
    pl = json.load(open(outdir + "/plan.json")); W = json.load(open(outdir + "/wallets.json")) if os.path.exists(outdir + "/wallets.json") else {}
    M = json.load(open(outdir + "/meta.json")) if os.path.exists(outdir + "/meta.json") else {}
    chains = json.load(open("out/amm/damm7_chains.json")).get("links", {})
    cen = json.load(open("out/amm/damm7.json"))["pools"]
    net = {p["creator"] for p in cen if p["sol"] >= 80} | {l.get("via") for l in chains.values() if l.get("via")} - {None}
    ctrls = json.load(open(outdir + "/controllers.json")) if os.path.exists(outdir + "/controllers.json") else {}
    net |= {v["address"] for v in ctrls.values()}                   # the controllers that pay the buyers' sweeps / creators' clean-ups
    CTL = json.load(open(outdir + "/control.json")) if os.path.exists(outdir + "/control.json") else {}
    SWEPT = set()                                                   # wallets a controller or creator co-signs for or funds (dammseat.py sweep)
    for fn in os.listdir(outdir):
        if fn.startswith("sweep_") and fn.endswith(".json"):
            sw = json.load(open(f"{outdir}/{fn}")); SWEPT |= set(sw["cosigners"]) | set(sw["funded"])
    P = []
    for it in pl["pick"]:
        T = json.load(open(f"{outdir}/tx/{it['pool']['pool']}.json")) if os.path.exists(f"{outdir}/tx/{it['pool']['pool']}.json") else None
        if T:
            P.append((it, events(T, it["pool"])))
    unit = lambda it: it["line"]
    # wallets: lines and pools they trade in
    w_lines, w_pools_line = collections.defaultdict(set), collections.defaultdict(lambda: collections.defaultdict(set))
    recv = collections.defaultdict(set)
    for it, ev in P:
        for e in ev:
            if e["k"] in ("buy", "sell"):
                w_lines[e["w"]].add(unit(it)); w_pools_line[e["w"]][unit(it)].add(it["pool"]["pool"])
            for f, t_, l in e["sys"]:
                if f in net and t_ not in net:
                    recv[t_].add(f)
    ff = lambda w: (W.get(w) or {}).get("funder")
    fleet = {w for w in w_lines if ff(w) in net or recv.get(w) or ((CTL.get(w) or {}).get("payer") in net and CTL[w]["payer"] != w)
             or set((CTL.get(w) or {}).get("signers", [])) & (net - {w}) or w in SWEPT}
    for _ in range(3):
        fleet |= {w for w in w_lines if ff(w) in fleet}
    fleet -= net

    def cls(w, line):
        if w in net:
            return "network"
        if w in fleet:
            return "fleet"
        if len(w_lines[w]) >= 3:
            return "bot"
        if len(w_pools_line[w][line]) >= 2:
            return "recur"
        return "out"
    first_cost = [e["cost"] for it, ev in P for e in ev if e["k"] == "buy" and ev[0]["slot"] <= e["slot"] <= ev[0]["slot"] + 2]
    all_cost = [e["cost"] for it, ev in P for e in ev if e["k"] in ("buy", "sell")]
    PIN, POUT = (pct(first_cost, 0.75) or 0), (med(all_cost) or 0)
    res = []
    by_line = collections.defaultdict(list)
    for it, ev in P:
        by_line[unit(it)].append((it, ev))
    for line, items in by_line.items():
        items.sort(key=lambda x: x[0]["pool"]["t"])
        known = set()                                                # fleet known live from earlier pools of the line
        bursts_prev = []
        for it, ev in items:
            p = it["pool"]; c = ev[0]["slot"]; t0 = ev[0]["t"]
            for e in ev:
                e["c"] = cls(e["w"], line) if e["k"] in ("buy", "sell") else e["k"]
            isf = lambda e: e["c"] in ("fleet", "recur")
            pull_i = next((i for i, e in enumerate(ev) if e["k"] == "pull"), None)
            end = pull_i if pull_i is not None else len(ev)
            pull_t = ev[pull_i]["t"] if pull_i is not None else None
            dep = ev[0]["sd"] if ev[0]["k"] == "create" else None
            buys = collections.Counter(); sells = collections.Counter(); nbuy = collections.Counter()
            for e in ev[:end]:
                if e["k"] == "buy":
                    buys[e["c"]] += e["sd"] / 1e9; nbuy[e["c"]] += 1
                elif e["k"] == "sell":
                    sells[e["c"]] += -e["sd"] / 1e9
            left = (ev[pull_i]["S0"] - dep) / 1e9 if pull_i is not None and dep else None
            netin = {k: round(buys[k] - sells[k], 4) for k in set(buys) | set(sells)}
            fb = [i for i in range(end) if ev[i]["k"] == "buy" and isf(ev[i]) and ev[i]["sd"] >= 0.01e9]
            burst = []
            if fb:
                burst = [fb[0]]
                for i in fb[1:]:
                    if ev[i]["slot"] - ev[burst[-1]]["slot"] <= 10:
                        burst.append(i)
                    else:
                        break
            price = lambda i: ev[i]["S"] / ev[i]["T"] if ev[i]["T"] > 0 else None
            pump = None
            if fb:
                last_f = max(fb); pb = ev[fb[0]]["S0"] / ev[fb[0]]["T0"] if ev[fb[0]]["T0"] else None
                pump = price(last_f) / pb if pb else None
            # pre-fleet outsider buys
            first_f = fb[0] if fb else end
            pre = [i for i in range(1, first_f) if ev[i]["k"] == "buy" and ev[i]["c"] == "out" and ev[i]["sd"] >= 0.01e9]
            case = None
            if pre:
                ws = {ev[i]["w"] for i in pre}
                held = sum(ev[i]["sd"] for i in pre if not any(e["k"] == "sell" and e["w"] == ev[i]["w"] for e in ev[i:first_f])) / 1e9
                case = {"sol": round(sum(ev[i]["sd"] for i in pre) / 1e9, 4), "held": round(held, 4), "first_s": ev[pre[0]]["t"] - t0,
                        "fleet_came": bool(fb), "pull_delay_s": (pull_t - ev[pre[-1]]["t"]) if pull_t else None,
                        "verified": sum(1 for w in ws if w in W and W[w].get("complete")), "wallets": len(ws)}
            # reaction: outsider buys >= 0.1 SOL in the 30 s before the pull, against the base rate of 30 s windows
            ob = [ev[i]["slot"] for i in range(1, end) if ev[i]["k"] == "buy" and ev[i]["c"] == "out" and ev[i]["sd"] >= 0.1e9]
            obt = [ev[i]["t"] for i in range(1, end) if ev[i]["k"] == "buy" and ev[i]["c"] == "out" and ev[i]["sd"] >= 0.1e9]
            react = None
            if pull_i is not None:
                ps = ev[pull_i]["slot"]; life = max(1, ps - c)
                cover = {s for b in ob for s in range(b, b + 3) if c < s <= ps}           # slots within 2 after an outsider buy
                react = {"after_out": any(b <= ps <= b + 2 for b in ob), "p_random": round(len(cover) / life, 3), "life_slots": life,
                         "last_out_to_pull_s": (pull_t - max(obt)) if obt else None, "out_buys_ge01": len(ob)}
            # implied fee
            imp = implied_fees(ev[:end]); mf = M.get(p["pool"], {})
            fee = max(mf.get("cliff") or 0, med([f for _, f in imp if f > -0.01]) or 0)
            # paper seat
            i_end = next((i for i, e in enumerate(ev) if e["slot"] > c + 1), len(ev))
            i_top = next((i for i, e in enumerate(ev) if e["slot"] > c), len(ev))
            live = known                                             # knowable live: wallets that bought in the line's earlier sampled pools
            lb = [i for i in range(i_end, end) if ev[i]["k"] == "buy" and ev[i]["w"] in live and ev[i]["sd"] >= 0.01e9]
            ex_burst = None
            if lb:
                b = [lb[0]]
                for i in lb[1:]:
                    if ev[i]["slot"] - ev[b[-1]]["slot"] <= 10:
                        b.append(i)
                    else:
                        break
                xs = ev[b[-1]]["slot"] + 10
                ex_burst = max(i for i, e in enumerate(ev) if e["slot"] <= xs)
            delay = med(bursts_prev) if bursts_prev else None
            ex_delay = max([i for i, e in enumerate(ev) if e["t"] <= t0 + delay] + [i_end - 1]) if delay is not None else None
            if ex_burst is None:                                     # no live-known fleet buy before the pull: time out at the delay
                ex_burst = ex_delay
            ex60 = max([i for i, e in enumerate(ev) if e["t"] <= t0 + 60] + [i_end - 1])
            seat = {}
            for tag, i0 in (("end", i_end), ("top", i_top)):
                for x in SIZES:
                    xl = int(x * 1e9); cost = PIN + POUT
                    for name, ex in (("burst", ex_burst), ("delay", ex_delay), ("s60", ex60)):
                        if ex is None or (tag == "top" and name != "burst"):
                            continue
                        v = replay(ev, i0, xl, max(ex, i0 - 1), fee)
                        seat[f"{tag}_{name}_{x}"] = round((v - xl - cost) / 1e9, 4) if v is not None else None
                    if tag == "end":
                        path = value_path(ev, i0, xl, fee, (pull_t or t0 + 3600))
                        if path:
                            seat[f"end_hind_{x}"] = round((max(v for _, v in path) - xl - cost) / 1e9, 4)
            r = {"line": line, "pool": p["pool"], "creator": p["creator"], "t": t0, "day": time.strftime("%m-%d", time.gmtime(t0)), "sol0": (dep or 0) / 1e9,
                 "n_ev": len(ev), "pull_s": (pull_t - t0) if pull_t else None, "left": left, "netin": netin,
                 "buys": {k: round(v, 4) for k, v in buys.items()}, "sells": {k: round(v, 4) for k, v in sells.items()}, "nbuy": dict(nbuy),
                 "fleet_first_s": (ev[fb[0]]["t"] - t0) if fb else None, "burst_end_s": (ev[burst[-1]]["t"] - t0) if burst else None,
                 "burst_sol": round(sum(ev[i]["sd"] for i in burst) / 1e9, 4), "pump": pump, "case": case, "react": react,
                 "fee": fee, "fee_cliff": mf.get("cliff"), "fee_implied_med": med([f for _, f in imp]), "dyn_fee": mf.get("dyn_init"),
                 "full_range": (mf.get("sqrt_min", 0) <= 4295048016 * 2 and mf.get("sqrt_max", 0) >= 79226673521066979257578248091 // 2) if mf else None,
                 "seat": seat, "delay_used": delay, "known_live": len(known)}
            res.append(r)
            known |= {e["w"] for e in ev[:end] if e["k"] == "buy" and e["sd"] >= 0.01e9}
            if r["burst_end_s"] is not None:
                bursts_prev.append(r["burst_end_s"])
    json.dump({"prio_in": PIN / 1e9, "prio_out": POUT / 1e9, "n_fleet": len(fleet), "n_network": len(net), "pools": res,
               "classes": dict(collections.Counter(cls(w, next(iter(w_lines[w]))) for w in w_lines))}, open(outdir + "/scan.json", "w"))
    report(outdir)


def report(outdir):
    d = json.load(open(outdir + "/scan.json")); R = d["pools"]
    f = lambda x, n=2: "-" if x is None else f"{x:.{n}f}"
    out = []
    pr = out.append
    pr("# DAMM v2 85-SOL pull lines: seat test\n")
    pr(f"{len(R)} pools; priority/tip per leg: entry {d['prio_in']:.6f} SOL (p75 of swaps in slots c..c+2), exit {d['prio_out']:.6f} SOL (median). "
       f"Wallet classes in the sample: {d['classes']}; fleet wallets (funded from the creator/relay network) {d['n_fleet']}.\n")
    fees = [r["fee"] for r in R]
    pr(f"Fees: base fee from the Pool account {sorted({r['fee_cliff'] for r in R if r['fee_cliff'] is not None})}; implied fee of the swaps (median per pool) "
       f"{f(min([r['fee_implied_med'] for r in R if r['fee_implied_med'] is not None], default=None), 5)}..{f(max([r['fee_implied_med'] for r in R if r['fee_implied_med'] is not None], default=None), 5)}; "
       f"dynamic fee on {sum(1 for r in R if r['dyn_fee'])} pools; full range {sum(1 for r in R if r['full_range'])} of {len(R)}.\n")
    lines = collections.defaultdict(list)
    for r in R:
        lines[r["line"]].append(r)
    pr("| line | pools (days) | pull s (median) | buy SOL share: fleet / recur / bot / out | SOL left at pull, median (net in: fleet / recur / bot / out, sum) | "
       "pre-fleet outsider cases: for / weak / against | reaction: pulls within 2 slots after an outsider buy >= 0.1 SOL, of pools with such buys (expected if timed at random) | pump x (fleet) | "
       "seat 0.5 / 1 / 2 SOL: burst exit | delay exit | +60 s | hindsight | verdict |")
    pr("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    summary = []
    for line, rs in sorted(lines.items(), key=lambda kv: (kv[0].startswith("contrast"), kv[0])):
        tb = collections.Counter(); tn = collections.Counter()
        for r in rs:
            for k, v in r["buys"].items():
                tb[k] += v
            for k, v in r["netin"].items():
                tn[k] += v
        tot = sum(tb.values()) or 1
        cases = [r for r in rs if r["case"]]
        clean = [r["pull_s"] for r in rs if not r["case"] and r["pull_s"]]
        minc = min(clean) if clean else None
        fo = fw = ag = 0
        for r in cases:
            c = r["case"]
            early = r["pull_s"] is not None and ((c["pull_delay_s"] is not None and c["pull_delay_s"] < 120) or (minc and r["pull_s"] < 0.8 * minc))
            if c["fleet_came"] and not early:
                if c["held"] >= 0.1:
                    fo += 1
                else:
                    fw += 1
            elif (not c["fleet_came"] and r["pull_s"] is not None) or early:
                ag += 1
            c["outcome"] = "tolerated" if c["fleet_came"] and not early else "early pull" if early else "skipped"
        with_f = sum(1 for r in rs if r["fleet_first_s"] is not None)
        pumps = [r["pump"] for r in rs if r["pump"]]
        if with_f < 0.5 * len(rs) or (med(pumps) or 0) < 1.3:
            verdict = "NO PUMP"
        elif fo >= 2 and not ag:
            verdict = "OPEN"
        elif ag >= 2 and ag > fo:
            verdict = "CLOSED"
        else:
            verdict = "UNKNOWN"
        rx = [r["react"] for r in rs if r["react"] and r["react"]["out_buys_ge01"]]
        S = lambda key: [sum(r["seat"].get(key.format(x=x)) or 0 for r in rs if r["seat"].get(key.format(x=x)) is not None) for x in SIZES]
        N = lambda key: sum(1 for r in rs if r["seat"].get(key.format(x=1.0)) is not None)
        sb, sd_, s6, sh = S("end_burst_{x}"), S("end_delay_{x}"), S("end_s60_{x}"), S("end_hind_{x}")
        days = sorted({r["day"] for r in rs})
        pr(f"| `{line}` | {len(rs)} ({', '.join(days)}) | {f(med([r['pull_s'] for r in rs if r['pull_s']]), 0)} | "
           f"{100 * tb['fleet'] / tot:.0f} / {100 * tb['recur'] / tot:.0f} / {100 * tb['bot'] / tot:.0f} / {100 * tb['out'] / tot:.0f}% of {tot:.1f} SOL | "
           f"{f(med([r['left'] for r in rs if r['left'] is not None]), 1)} ({tn['fleet']:+.1f} / {tn['recur']:+.1f} / {tn['bot']:+.1f} / {tn['out']:+.1f}) | "
           f"{fo} / {fw} / {ag} | {sum(1 for x in rx if x['after_out'])}/{len(rx)} (expected {sum(x['p_random'] for x in rx):.1f}) | {f(med(pumps))} | "
           f"{'/'.join(f'{v:+.2f}' for v in sb)} (n {N('end_burst_{x}')}) | {'/'.join(f'{v:+.2f}' for v in sd_)} (n {N('end_delay_{x}')}) | "
           f"{'/'.join(f'{v:+.2f}' for v in s6)} | {'/'.join(f'{v:+.2f}' for v in sh)} | {verdict} |")
        summary.append({"line": line, "verdict": verdict, "for": fo, "weak": fw, "against": ag})
    pr("\nPer pool:\n")
    for r in sorted(R, key=lambda r: (r["line"], r["t"])):
        c = r["case"]
        pr(f"- {r['line'][:40]} `{r['pool']}` {r['day']}: deposit {r['sol0']:.2f} SOL, pull at {f(r['pull_s'], 0)} s, left {f(r['left'], 2)} SOL; "
           f"buys {r['buys']}; net in {r['netin']}; fleet first buy {f(r['fleet_first_s'], 0)} s, first burst {r['burst_sol']} SOL to {f(r['burst_end_s'], 0)} s, pump x{f(r['pump'])}; "
           f"fee {r['fee']:.5f}; " + (f"pre-fleet outsiders {c['sol']} SOL (held {c['held']}) from +{c['first_s']} s, fleet came {c['fleet_came']}, pull {c['pull_delay_s']} s later -> {c.get('outcome')}; " if c else "")
           + (f"reaction: pull within 2 slots of an outsider buy {r['react']['after_out']} (random {r['react']['p_random']}), last outsider buy >= 0.1 SOL {r['react']['last_out_to_pull_s']} s before; " if r['react'] else "")
           + f"seat 1 SOL burst {r['seat'].get('end_burst_1.0')} delay {r['seat'].get('end_delay_1.0')} +60 s {r['seat'].get('end_s60_1.0')} hind {r['seat'].get('end_hind_1.0')}")
    open(outdir + "/seatreport.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out[:20 + len(lines)]))


if __name__ == "__main__":
    main(sys.argv[1])
