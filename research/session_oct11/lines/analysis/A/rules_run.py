"""Step 2: the brief's replay rules per candidate line, all days and per day (day 6 = the last 24 h), q = 0.0058 and 0.002 ETH.
Also: the first real buy (offset, size, fingerprint share, % price move), and our buy's effect on its output."""
import math
from cands import *
from replay import *
rows = rows_nonvbot(); E = load_ev()
RES = {}


def frb_info(r, P):
    f = r.get("frb")
    if not f or f["idx"] >= len(P["sw"]): return None
    w = P["sw"][f["idx"]]
    # state before that swap
    prev = [x for x in P["sw"][:f["idx"]]]
    s_b = prev[-1]["sqrt"] if prev else P["s0"]
    mv = (s_b / w["sqrt"]) ** 2 - 1 if P["qs"] == 0 else (w["sqrt"] / s_b) ** 2 - 1
    return {"off": f["off"], "eth": f["eth"], "fp": f"{f['to']}:{f['sel']}:{f['clen']}", "move": mv, "w": w, "s_before": s_b}


def our_impact(r, P, fi, q_eth, a=2):
    """with our q bought at L+a (a < frb block), the operator's frb output vs without: 1 - out_with/out_without"""
    if fi is None or fi["off"] <= a: return None
    A = P["lb"] + a; s, L, fee = state_before(P, A)
    s1, _ = buy_step(P["qs"], s, L, q_units(r, q_eth), fee)
    sa, sb = s1, s
    for w in P["sw"]:
        if w["bn"] < A: continue
        if w is fi["w"]:
            o_with = buy_step(P["qs"], sa, w["L"], w["inp"], w["fee"])[1]; o_wo = buy_step(P["qs"], sb, w["L"], w["inp"], w["fee"])[1]
            return 1 - o_with / o_wo if o_wo else None
        if w["buy"]: sa = buy_step(P["qs"], sa, w["L"], w["inp"], w["fee"])[0]; sb = buy_step(P["qs"], sb, w["L"], w["inp"], w["fee"])[0]
        else: sa = sell_step(P["qs"], sa, w["L"], w["inp"], w["fee"])[0]; sb = sell_step(P["qs"], sb, w["L"], w["inp"], w["fee"])[0]
    return None


def run(name, rs, verbose=True):
    rs = [r for r in rs if r["dex"] == "v4"]
    Ps = {r["pool"]: prep(r, E[r["pool"]]) for r in rs}
    rs = [r for r in rs if Ps[r["pool"]]["L0"] > 0]
    n = len(rs); per_day = n / 7.0
    FI = {r["pool"]: frb_info(r, Ps[r["pool"]]) for r in rs}
    fis = [x for x in FI.values() if x]
    topfp = C.Counter(x["fp"] for x in fis).most_common(1)[0] if fis else (None, 0)
    offs = [x["off"] for x in fis]
    H = min(600, int(math.ceil(pct(offs, 0.9))) + 1) if offs else 60
    out = {"n": n, "per_day": round(per_day, 1), "days": [sum(1 for r in rs if day_of(r) == d) for d in range(7)], "frb_share": round(len(fis) / n, 3) if n else 0,
           "frb_off": p1050(offs), "frb_eth": p1050([x["eth"] for x in fis]), "frb_top_fp": topfp, "frb_move_pct": p1050([100 * x["move"] for x in fis]), "fallback_hold": H}
    imp = {}
    for q in (0.0058, 0.002):
        v = [our_impact(r, Ps[r["pool"]], FI[r["pool"]], q) for r in rs]; v = [x for x in v if x is not None]
        imp[str(q)] = p1050([100 * x for x in v])
    out["our_impact_on_frb_output_pct"] = imp
    rules = {}

    def add(rule, fab, q, subset=None):
        res_all = []; byday = C.defaultdict(list)
        for r in (subset if subset is not None else rs):
            ab = fab(r)
            if ab is None: continue
            a, b = ab
            if a < 1: continue
            x = replay(r, Ps[r["pool"]], a, b, q)
            if x is None: continue
            res_all.append(x); byday[day_of(r)].append(x)
        trad = len(res_all) / n if n else 0
        st = stats(res_all, per_day, trad); st["tradable_share"] = round(trad, 3)
        st["by_day"] = {d: stats(byday[d]) for d in range(7)}
        rules[f"{rule}|q={q}"] = st

    for q in (0.0058, 0.002):
        frbo = lambda r: FI[r["pool"]]["off"] if FI[r["pool"]] else None
        add("front a2 b=frb+1 (frb pools)", lambda r: (2, max(frbo(r) + 1, 3)) if frbo(r) is not None and frbo(r) >= 2 else None, q)
        add(f"front a2 b=frb+1 else a+{H}", lambda r: (2, max(frbo(r) + 1, 3)) if frbo(r) is not None and frbo(r) >= 2 and frbo(r) + 1 <= 2 + H else (2, 2 + H), q)
        for b in (10, 20, 40, 60, 100, 150, 200, 300):
            add(f"front a2 b{b}", lambda r, b=b: (2, b), q)
        for k in (2, 3, 4, 5, 6):
            add(f"delayed(oracle) a=frb-{k} b=a+60", lambda r, k=k: (frbo(r) - k, frbo(r) - k + 60) if frbo(r) is not None and frbo(r) - k >= 1 else None, q)
        if offs:
            fa = max(1, int(pct(offs, 0.1)) - 2)
            add(f"delayed(fixed) a={fa} b=a+60", lambda r, fa=fa: (fa, fa + 60), q)
        add("follow a=frb+2 b=a+20", lambda r: (frbo(r) + 2, frbo(r) + 22) if frbo(r) is not None else None, q)
        add("follow a=frb+2 b=a+60", lambda r: (frbo(r) + 2, frbo(r) + 62) if frbo(r) is not None else None, q)
    out["rules"] = rules
    RES[name] = out
    if verbose:
        print(f"\n===== {name}: n={n} ({out['per_day']}/day) days={out['days']} frb={out['frb_share']} off={out['frb_off']} eth={out['frb_eth']} topfp={topfp} move%={out['frb_move_pct']} "
              f"our impact on frb out % (q=.0058 / .002)={imp} fallback_hold={H}")
        for k, st in rules.items():
            if st.get("n", 0) == 0: continue
            dd = " ".join(f"d{d}:{st['by_day'][d].get('n',0)}/{st['by_day'][d].get('mean','-')}" for d in range(7))
            print(f"  {k:52s} n={st['n']:4d} trad={st['tradable_share']:.2f} mean={st['mean']:+.4f} med={st['median']:+.4f} win={st['win']:.2f} worst={st['worst']:+.3f} pulled={st['pulled']:.3f} $/tr={st['mean_usd']:+.4f} $/day={st['usd_day']:+.2f} | {dd}")


if __name__ == "__main__":
    for name, f in CANDS.items():
        if name.startswith("v0_1444"): continue
        run(name, [r for r in rows if f(r)])
    json.dump(RES, open(os.path.join(OUT, "rules_results.json"), "w"), indent=0, default=str)
