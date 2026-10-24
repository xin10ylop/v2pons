#!/usr/bin/env python3
"""pumpscan.py OUTDIR [MIN_SAMPLED]: the pump.fun wave model tested on pumpwave.py's launches (offline: reads OUTDIR only).

Wallet classes, per operator (pumpops.py's merged creators):
  dev      the operator's creators (fee payers of its launches)
  agent    pump.fun's Mayhem-mode agent (BwWK17cb...; trades Mayhem launches fee-free): neither the operator nor an outsider
  generic  buys in sampled launches of 3+ different operators (snipers and bots): outsiders, the competition for the first seat
  op       (strict, 'linked') not generic, and one of: buys in the creation slot (the bundle); received SOL from the operator's
           creators or funder from 30 min before to 15 min after a sampled launch (pumpwave.py links); first funded (oldest
           transaction's SOL sender) by the creators, the funder, or another op wallet; or first funded by a (non-hub) parent that
           also first-funded single-launch buyers in another of the operator's launches
  recur    not generic, not linked, buys in 2+ of the operator's sampled launches: the brief counts these as operator wallets, but
           many are dev-tracking snipers (they buy right after the creation and the dev sells into them); kept apart
  out      everything else that buys: an outsider; 'verified' when its first funder was looked up and is not linked
The wave is reported with the brief's definition (dev + op + recur buys after slot c: wave_sol, has_wave) and strictly (dev + op
only: wave_strict_sol, has_wave_strict). The dump clock uses dev + op (strict) sells.
Per launch (creation slot c, the first 15 min):
  dev buy (SOL incl. fees, in the creation slot), bundle (non-dev buys in slot c: op wallets / generic snipers / the agent),
  wave = dev, op and recur buys after slot c (SOL, count, first and last slot, seconds), has_wave = wave SOL >= WAVE_MIN,
  dump = dev and op sells: the clock is the slot (and second) of the first big one (>= 10% of the op wallets' tokens at the time and
  >= 0.01 SOL) and of the slot with the most op selling (peak), counted from c,
  first seats: buys by generic/out wallets in slots c+1..c+2 (>= 0.01 SOL): contested if any,
  lift: the price after the last wave buy and the peak price before the first big dump, over the price at the end of slot c,
  graduated within 15 min.
Paper trade (per launch, in time order within the operator): buy X SOL in slot c+1 ('end': after every trade in c+1; 'top': before
  them), others' buys keep their SOL and sells their tokens (our impact replayed on the virtual reserves, constant product; a Mayhem-
  agent trade moves the reserves by its actual change, since the agent shifts the curve's virtual SOL far beyond its trade), sell at
  the end of slot c + median(first-big-dump clock of the operator's EARLIER sampled launches, at least 2) - 1. Fees: the TradeEvents'
  protocol + creator rate on each leg (1.25% at launch), plus per-leg priority cost: entry = 75th percentile of (tx fee + Jito tip)
  of first-seat buyers, exit = median (tx fee + Jito tip) of all trades. Benchmarks: the best exit slot in the 15 min (hindsight)
  and the end of the second +60 s. Variant 'paper25': sell before the 25th percentile of the earlier launches' clocks instead.
Writes OUTDIR/wave.json and prints a summary; pumpreport.py makes the tables."""
import json, os, sys, glob, time, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P

SIZES = (0.1, 0.5, 1.0)
WAVE_MIN = float(os.environ.get("WAVE_MIN", "0.2"))
GRAD = {}
DUST = 0.01
med = lambda xs: st.median(xs) if xs else None


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def events(T):
    ev = []
    for r in T["rows"]:
        for k, (u, b, sol, tok, fee, fbps, vS, vT, rT) in enumerate(r["ev"]):
            ev.append({"slot": r["slot"], "idx": r["idx"] or 0, "k": k, "t": r["t"], "u": u, "buy": bool(b), "sol": sol, "tok": tok, "fbps": fbps,
                       "vS": vS, "vT": vT, "rT": rT, "cost": r["txfee"] + r["tip"], "payer": r["payer"], "sig": r["sig"], "complete": r["complete"]})
    ev.sort(key=lambda e: (e["slot"], e["idx"], e["k"]))
    return ev


V0 = (30_000_000_000, 1_073_000_000_000_000, 793_100_000_000_000)        # a SOL curve at creation (CreateEvent; checked in pumpcensus)


def state(ev, i0):
    return (ev[i0 - 1]["vS"], ev[i0 - 1]["vT"], ev[i0 - 1]["rT"]) if i0 > 0 else V0


def step(ev, i, st_):
    """apply ev[i] to our replayed state (vS, vT, rT): a trader's buy keeps its SOL in, a sell its tokens (constant product on the
    virtual reserves, our position included); a Mayhem-agent trade moves the reserves by its actual on-chain change (the agent
    shifts the curve's virtual SOL by far more than its trade: verified, every non-agent event chains exactly, agent events do not).
    Returns the new state, or None when the curve would complete (real tokens run out)."""
    vS, vT, rT = st_; e = ev[i]
    if e["u"] == P.MAYHEM_AGENT:
        aS, aT, aR = state(ev, i)
        return vS + e["vS"] - aS, vT + e["vT"] - aT, rT + e["rT"] - aR
    if e["buy"]:
        o = P.buy_tokens(vS, vT, e["sol"])
        if o > rT:
            return None
        return vS + e["sol"], vT - o, rT - o
    o = P.sell_sol(vS, vT, e["tok"])
    return vS - o, vT + e["tok"], rT + e["tok"]


def replay(ev, i0, x, exit_i, f_buy, f_sell):
    """our buy of x SOL before ev[i0] (state after ev[i0-1]), others replayed, our sell after ev[exit_i]; returns SOL back
    (None if the curve completes first)"""
    vS, vT, rT = state(ev, i0)
    net = int(x * 1e9 / (1 + f_buy)); q = P.buy_tokens(vS, vT, net)
    if q > rT:
        return None
    st_ = (vS + net, vT - q, rT - q)
    for i in range(i0, exit_i + 1):
        st_ = step(ev, i, st_)
        if st_ is None:
            return None
    return P.sell_sol(st_[0], st_[1], q) * (1 - f_sell) / 1e9


def value_path(ev, i0, x, f_buy, f_sell, t_end):
    """our sell value after each event from i0 on (to t_end): [(i, value)]"""
    vS, vT, rT = state(ev, i0)
    net = int(x * 1e9 / (1 + f_buy)); q = P.buy_tokens(vS, vT, net)
    if q > rT:
        return []
    st_ = (vS + net, vT - q, rT - q)
    out = [(i0 - 1, P.sell_sol(st_[0], st_[1], q) * (1 - f_sell) / 1e9)]
    for i in range(i0, len(ev)):
        if ev[i]["t"] > t_end:
            break
        st_ = step(ev, i, st_)
        if st_ is None:
            break
        out.append((i, P.sell_sol(st_[0], st_[1], q) * (1 - f_sell) / 1e9))
    return out


def main(outdir, min_sampled):
    ops = P.jload(outdir + "/operators.json"); wallets = P.jload(outdir + "/wallets.json", {}); hubs = P.jload(outdir + "/hubs.json", {})
    global GRAD
    GRAD = P.jload(outdir + "/grad.json", {})
    TR = {}
    for o in ops:
        for L in o["launches"]:
            T = P.jload(f"{outdir}/trades/{L['mint']}.json")
            if T:
                TR[L["mint"]] = (L, T, events(T))
    print(f"{len(TR)} launches with trades read", flush=True)
    # generic wallets: buy in sampled launches of 3+ operators
    w_ops = collections.defaultdict(set)
    for o in ops:
        for L in o["launches"]:
            if L["mint"] in TR:
                for e in TR[L["mint"]][2]:
                    if e["buy"]:
                        w_ops[e["u"]].add(o["id"])
    generic = {w for w, s in w_ops.items() if len(s) >= 3} - {P.MAYHEM_AGENT}
    # priority cost: first-seat buyers (slots c+1..c+2, not the creator) and every trade
    first_cost, all_cost = [], []
    for L, T, ev in TR.values():
        for e in ev:
            all_cost.append(e["cost"])
            if L["slot"] < e["slot"] <= L["slot"] + 2 and e["buy"] and e["u"] != L["payer"] and e["u"] != P.MAYHEM_AGENT:
                first_cost.append(e["cost"])
    PRIO_IN = (pct(first_cost, 0.75) or 0) / 1e9; PRIO_OUT = (med(all_cost) or 0) / 1e9
    print(f"priority cost per leg: entry {PRIO_IN:.6f} SOL (p75 of {len(first_cost)} first-seat buys; median {med(first_cost) / 1e9:.6f}), "
          f"exit {PRIO_OUT:.6f} SOL (median of {len(all_cost)} trades)", flush=True)
    res = []
    for o in ops:
        ls = [TR[L["mint"]] for L in o["launches"] if L["mint"] in TR]
        if len(ls) < min_sampled:
            continue
        res.append(analyse(o, ls, generic, wallets, hubs, outdir, PRIO_IN, PRIO_OUT))
    P.jsave(outdir + "/wave.json", {"prio_in": PRIO_IN, "prio_out": PRIO_OUT, "first_cost_median": (med(first_cost) or 0) / 1e9,
                                    "n_generic": len(generic), "wave_min": WAVE_MIN, "ops": res})
    print(f"{len(res)} operators analysed -> {outdir}/wave.json", flush=True)


def analyse(o, ls, generic, wallets, hubs, outdir, PRIO_IN, PRIO_OUT):
    C = set(o["members"]); F = {f for f in o["funders"] if not hubs.get(f, {}).get("hub")}
    flows = (P.jload(f"{outdir}/outflows/{o['id']}.json") or {}).get("sent", {})
    R = set(flows)
    rec = collections.Counter()
    for L, T, ev in ls:
        rec.update({e["u"] for e in ev if e["buy"]})
    ff = lambda w: (wallets.get(w) or {}).get("funder")
    bundle = set()
    for L, T, ev in ls:
        bundle |= {e["u"] for e in ev if e["buy"] and e["slot"] == L["slot"] and e["u"] not in generic and e["u"] != P.MAYHEM_AGENT and e["u"] not in C}
    funded = (R - generic - C)                                       # received SOL from the creators / funder around a launch
    linked = set(C) | funded | bundle
    for _ in range(3):                                               # first funded by the creators, the funder, or a linked wallet
        linked |= {w for w in rec if w not in generic and w != P.MAYHEM_AGENT and ff(w) and (ff(w) in linked or ff(w) in F)}
    byparent = collections.defaultdict(set)                          # a parent funding single-launch buyers in 2+ launches
    for L, T, ev in ls:
        for e in ev:
            if e["buy"] and rec[e["u"]] == 1 and e["u"] not in generic and ff(e["u"]) and not hubs.get(ff(e["u"]), {}).get("hub"):
                byparent[ff(e["u"])].add(L["mint"])
    parents = {a for a, ms in byparent.items() if len(ms) >= 2}
    linked |= {w for w in rec if w not in generic and ff(w) in parents}
    linked -= {P.MAYHEM_AGENT}
    recur = {w for w, k in rec.items() if k >= 2 and w not in generic and w != P.MAYHEM_AGENT} - linked
    op = linked | recur                                              # the brief's operator wallets: dev, bundle, recurring, funded

    def cls(w):
        if w in C:
            return "dev"
        if w == P.MAYHEM_AGENT:
            return "agent"
        if w in linked:
            return "op"
        if w in recur:
            return "recur"
        if w in generic:
            return "generic"
        return "out"
    out = []
    for L, T, ev in ls:
        c = L["slot"]; t0 = L["t"]
        for e in ev:
            e["c"] = cls(e["u"])
        ops_ = lambda e: e["c"] in ("dev", "op")                        # strict: dev, bundle, funded
        opu_ = lambda e: e["c"] in ("dev", "op", "recur")              # the brief's definition, recurring wallets included
        dev_sol = sum(e["sol"] * (1 + e["fbps"] / 1e4) for e in ev if e["slot"] == c and e["buy"] and e["c"] == "dev") / 1e9
        bundle = [e for e in ev if e["slot"] == c and e["buy"] and e["c"] != "dev"]
        b_op = [e for e in bundle if e["c"] == "op"]
        wave_i = [i for i, e in enumerate(ev) if e["slot"] > c and e["buy"] and opu_(e)]
        wave = [ev[i] for i in wave_i]
        wave_sol = sum(e["sol"] for e in wave) / 1e9
        wave_strict = sum(e["sol"] for e in ev if e["slot"] > c and e["buy"] and ops_(e)) / 1e9
        recur_sold = sum(e["sol"] for e in ev if e["c"] == "recur" and not e["buy"]) / 1e9
        # dump clock
        held = 0; first_big = None; sells = collections.Counter()
        for i, e in enumerate(ev):
            if not ops_(e):
                continue
            if e["buy"]:
                held += e["tok"]
            else:
                if first_big is None and e["sol"] >= DUST * 1e9 and e["tok"] >= 0.1 * max(held, 1):
                    first_big = i
                held -= e["tok"]; sells[e["slot"]] += e["sol"]
        peak_slot = max(sells, key=sells.get) if sells else None
        # price lift
        end_c = max((i for i, e in enumerate(ev) if e["slot"] <= c), default=None)
        p = lambda i: ev[i]["vS"] / ev[i]["vT"] if ev[i]["vT"] else None
        p0 = p(end_c) if end_c is not None else V0[0] / V0[1]
        lift_wave = lift_peak = None
        if p0:
            last_w = wave_i[-1] if wave_i else None
            if last_w is not None:
                lift_wave = p(last_w) / p0
            stop = first_big if first_big is not None else len(ev)
            pk = max((p(i) for i in range((end_c or 0), stop) if p(i)), default=None)
            lift_peak = pk / p0 if pk else None
        seats = [e for e in ev if c < e["slot"] <= c + 2 and e["buy"] and e["c"] in ("generic", "out") and e["sol"] >= DUST * 1e9]
        seat_wallets = sorted({e["u"] for e in seats})
        verified = [w for w in seat_wallets if w in generic or (w in wallets and rec[w] == 1 and ff(w) not in op and ff(w) not in F)]
        outs = {e["u"] for e in ev if e["buy"] and e["c"] in ("generic", "out")}
        fb = [e["fbps"] for e in ev if e["fbps"] > 0]
        rec_l = {"mint": L["mint"], "t": t0, "day": time.strftime("%m-%d", time.gmtime(t0)), "slot": c, "creator": L["payer"],
                 "mayhem": T.get("mayhem"), "n_ev": len(ev), "truncated": T["truncated"], "dev_sol": round(dev_sol, 4),
                 "bundle_n": len(bundle), "bundle_op_sol": round(sum(e["sol"] for e in b_op) / 1e9, 4),
                 "bundle_generic_sol": round(sum(e["sol"] for e in bundle if e["c"] == "generic") / 1e9, 4),
                 "bundle_agent_sol": round(sum(e["sol"] for e in bundle if e["c"] == "agent") / 1e9, 4),
                 "wave_sol": round(wave_sol, 4), "wave_n": len(wave), "has_wave": wave_sol >= WAVE_MIN,
                 "wave_strict_sol": round(wave_strict, 4), "has_wave_strict": wave_strict >= WAVE_MIN, "recur_sold": round(recur_sold, 4),
                 "seat_recur": len({e["u"] for e in ev if c < e["slot"] <= c + 2 and e["buy"] and e["c"] == "recur" and e["sol"] >= DUST * 1e9}),
                 "wave_first_slot": (wave[0]["slot"] - c) if wave else None, "wave_last_slot": (wave[-1]["slot"] - c) if wave else None,
                 "wave_s": (wave[-1]["t"] - wave[0]["t"]) if wave else None, "wave_end_s": (wave[-1]["t"] - t0) if wave else None,
                 "agent_buy_sol": round(sum(e["sol"] for e in ev if e["c"] == "agent" and e["buy"]) / 1e9, 4),
                 "op_sell_sol": round(sum(sells.values()) / 1e9, 4),
                 "clock_slot": (ev[first_big]["slot"] - c) if first_big is not None else None,
                 "clock_s": (ev[first_big]["t"] - t0) if first_big is not None else None,
                 "peak_slot": (peak_slot - c) if peak_slot is not None else None,
                 "lift_wave": lift_wave, "lift_peak": lift_peak,
                 "outsiders": len(outs), "seat_n": len(seat_wallets), "seat_verified": len(verified), "seat_sol": round(sum(e["sol"] for e in seats) / 1e9, 4),
                 "contested": bool(seats), "graduated": any(e["complete"] for e in ev), "graduated_now": GRAD.get(L["mint"]),
                 "fee_bps": med(fb[:5]) if fb else 125}
        rec_l["_ev"] = ev
        out.append(rec_l)
    out.sort(key=lambda r: r["t"])
    # out-of-sample paper trade
    for k, r in enumerate(out):
        ev = r.pop("_ev"); c = r["slot"]
        prior = [q["clock_slot"] for q in out[:k] if q["clock_slot"] is not None]
        r["prior_clock"] = med(prior) if len(prior) >= 2 else None
        r["prior_p25"] = pct(prior, 0.25) if len(prior) >= 2 else None
        f = (r["fee_bps"] or 125) / 1e4
        i_top = next((i for i, e in enumerate(ev) if e["slot"] > c), len(ev))
        i_end = next((i for i, e in enumerate(ev) if e["slot"] > c + 1), len(ev))
        r["paper"] = {}; r["hind"] = {}; r["s60"] = {}; r["paper25"] = {}
        for tag, i0 in (("end", i_end), ("top", i_top)):
            for x in SIZES:
                key = f"{tag}{x}"
                path = value_path(ev, i0, x, f, f, r["t"] + 900)
                cost = PRIO_IN + PRIO_OUT
                if path:
                    r["hind"][key] = round(max(v for _, v in path) - x - cost, 5)
                    v60 = [v for i, v in path if i < 0 or ev[i]["t"] <= r["t"] + 60]
                    r["s60"][key] = round(v60[-1] - x - cost, 5) if v60 else None
                if r["prior_clock"] is not None:
                    xs = c + max(1, int(r["prior_clock"]) - 1)
                    exit_i = max([i for i, e in enumerate(ev) if e["slot"] <= xs] + [i0 - 1])
                    v = replay(ev, i0, x, exit_i, f, f) if exit_i >= i0 - 1 else None
                    r["paper"][key] = round(v - x - cost, 5) if v is not None else None
                if tag == "end" and r["prior_p25"] is not None:
                    xs = c + max(1, int(r["prior_p25"]) - 1)
                    exit_i = max([i for i, e in enumerate(ev) if e["slot"] <= xs] + [i0 - 1])
                    v = replay(ev, i0, x, exit_i, f, f)
                    r["paper25"][key] = round(v - x - cost, 5) if v is not None else None
        r["exit_slot"] = (max(1, int(r["prior_clock"]) - 1)) if r["prior_clock"] is not None else None
        r["dump_before_exit"] = (r["clock_slot"] is not None and r["exit_slot"] is not None and r["clock_slot"] <= r["exit_slot"])
    return {"id": o["id"], "members": o["members"], "funders": o["funders"], "funder_hub": o.get("funder_hub"), "n_window": o["n"],
            "per_day": o["per_day"], "service_share": o["service_share"], "n_sampled": len(out), "n_op_wallets": len(op - C),
            "n_linked": len(linked - C), "n_recur": len(recur), "n_bundle": len(bundle), "n_funded": len(funded),
            "n_parents": len(parents), "launches": out}


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
