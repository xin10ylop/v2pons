"""per kept family: price all 2,574 rules (18 K x 143 exits) and choose a rule three ways.
 V  ("validated", the brief's ranking): fit mean > 0 on days 1-5 (n >= 10), validation mean > 0 on days 6-7 (n >= 5), every 6-hour slice of the
    7 days with >= 3 trades positive; the rule with the highest validated $/day (validation = the last 48 h, so $/day = the sum of the
    validation trades' $ / 2). If no rule has every slice positive, the best by share of positive slices then validated $/day (tagged).
 F  (fit-only, out of sample): the best fit total on days 1-5 among rules whose fit slices are all positive; reported on days 6-7.
 W  (walk-forward, out of sample): V's selection run on days 1-6 only (fit 1-5, check day 6, slices 0-23); reported on day 7 (the last 24 h).
K = 0 (buy in the launch block) is an upper bound and never selected. argv: q (default 0.0058)"""
from gstats import *
Q = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0058
USD = Q * ETH_USD
rows = {r["pool"]: r for r in load_rows()}
kept = json.load(open(os.path.join(G, "families_kept.json")))
grid = load_grid(Q)
KNOWN_TOK = {"a98b3b9e": "a98b", "58d59320": "58d59320"}
NOK0 = np.arange(18)[:, None] >= 1

def pick(score, ok):
    if not ok.any(): return None
    a = int(np.argmax(np.where(ok, score, -np.inf))); return a // gsim.NR, a % gsim.NR

res = []
for fk, pools in kept.items():
    rs = [rows[p] for p in pools]
    ts = np.array([r["launch_ts"] for r in rs]); dy = np.array([day(t) for t in ts]); sl = np.array([slice6(t) for t in ts])
    fit = ts < FIT_END; val = ~fit; d6 = dy == 5; d7 = dy == 6
    ret, pulled, so = fam_returns(grid, pools)
    fm, fc, fs = agg(ret, fit); vm, vc, vs = agg(ret, val); m6, c6, s6 = agg(ret, d6); m7, c7, s7 = agg(ret, d7)
    sm = np.full((28,) + fm.shape, np.nan); scn = np.zeros((28,) + fm.shape, int)
    for s in range(28):
        msk = sl == s
        if msk.any(): sm[s], scn[s], _ = agg(ret, msk)
    q3 = scn >= 3; pos3 = q3 & (sm > 0)
    n3_all, p3_all = q3.sum(0), pos3.sum(0)
    n3_fit, p3_fit = q3[:20].sum(0), pos3[:20].sum(0)
    n3_val, p3_val = q3[20:].sum(0), pos3[20:].sum(0)
    n3_w, p3_w = q3[:24].sum(0), pos3[:24].sum(0)
    base = NOK0 & (fc >= 10) & (fm > 0)
    okV = base & (vc >= 5) & (vm > 0)
    cleanV = okV & (p3_all == n3_all)
    selV = pick(vs, cleanV); tagV = "all slices positive"
    if selV is None:
        selV = pick((p3_all / np.maximum(n3_all, 1)) * 1e9 + vs, okV); tagV = "not every slice positive"
    if selV is None: tagV = "no rule positive on both fit and validation"
    selF = pick(fs, base & (p3_fit == n3_fit))
    okW = base & (c6 >= 3) & (m6 > 0)
    selW = pick(s6, okW & (p3_w == n3_w))
    if selW is None: selW = pick((p3_w / np.maximum(n3_w, 1)) * 1e9 + s6, okW)
    n48 = int((ts >= LAST48).sum())
    quotes = C.Counter(r["quote"] for r in rs); hooks = sum(r["hooks"] != ZERO for r in rs)
    kf = C.Counter(r["known_fp"] for r in rs if r["known_fp"])
    toks = C.Counter((r["fam"].get("tok") or "")[:8] for r in rs)
    known = [f"{k} {v}" for k, v in kf.most_common()] + [f"{KNOWN_TOK[t]} {n}" for t, n in toks.items() if t in KNOWN_TOK]
    o = {"fam": fk, "n": len(pools), "n48": n48, "per_day48": n48 / 2, "n24": int(d7.sum()), "quotes": dict(quotes), "hooked": hooks, "known": known,
         "tagV": tagV, "n_rules_pass_all": int(cleanV.sum()), "n_rules_fit_val_pos": int(okV.sum())}
    def st(ki, ri, msk):
        d = one(ret[msk, ki, ri], pulled[msk, ki, ri]); d["launches"] = int(msk.sum())
        if d["n"]: d["usd_per_trade"] = d["mean"] * USD; d["usd_sum"] = d["mean"] * USD * d["n"]
        return d
    def block(sel, kind):
        if sel is None: return None
        ki, ri = sel; K = gsim.KS[ki]
        b = {"rule": gsim.rule_name(K, ri), "K": K, "ki": int(ki), "ri": int(ri), "fit": st(ki, ri, fit), "val": st(ki, ri, val),
             "all": st(ki, ri, np.ones(len(ts), bool)), "d6": st(ki, ri, d6), "last24": st(ki, ri, d7),
             "slices_all": [int(n3_all[ki, ri]), int(p3_all[ki, ri])], "slices_fit": [int(n3_fit[ki, ri]), int(p3_fit[ki, ri])],
             "slices_val": [int(n3_val[ki, ri]), int(p3_val[ki, ri])],
             "per_day": [st(ki, ri, dy == d) for d in range(7)],
             "slices": [[s, int(scn[s, ki, ri]), None if np.isnan(sm[s, ki, ri]) else round(float(sm[s, ki, ri]), 5)] for s in range(28)],
             "k0_bound": one(ret[:, 0, ri], pulled[:, 0, ri])}
        v = b["val"]; b["val_usd_day"] = v.get("usd_sum", 0.0) / 2
        b["last24_usd_day"] = b["last24"].get("usd_sum", 0.0)
        return b
    o["V"] = block(selV, "V"); o["F"] = block(selF, "F"); o["W"] = block(selW, "W")
    if o["V"]:
        # the spread among passing rules: validated $/day of the 10 best, and the median over all passing rules
        vv = np.where(cleanV if cleanV.any() else okV, vs / 2 * USD, np.nan).ravel(); vv = vv[~np.isnan(vv)]
        o["passing_val_usd_day_median"] = float(np.median(vv)) if len(vv) else None
    o["val_usd_day"] = o["V"]["val_usd_day"] if o["V"] else None
    res.append(o)
res.sort(key=lambda o: (o["V"] is not None and o["tagV"] == "all slices positive", o["val_usd_day"] if o["val_usd_day"] is not None else -1e9), reverse=True)
json.dump(res, open(os.path.join(G, f"g06_results_q{Q}.json"), "w"), indent=1)
def f(x): return "-" if x is None else f"{x*100:+.1f}%"
print(f"q = {Q} ETH; families {len(res)}; V passing every slice: {sum(1 for o in res if o['V'] and o['tagV']=='all slices positive')}; "
      f"V positive fit and validation (some slice negative): {sum(1 for o in res if o['V'] and o['tagV']!='all slices positive')}; none: {sum(1 for o in res if not o['V'])}")
for i, o in enumerate(res):
    V, F, W = o["V"], o["F"], o["W"]
    if not V:
        print(f"{i+1:3d} {o['fam'][:100]:100s} n {o['n']:5d} /d48 {o['per_day48']:6.1f} | {o['tagV']}" + (f" | F {F['rule']} val {f(F['val'].get('mean'))} n {F['val']['n']}" if F else "")); continue
    v = V["val"]
    s = (f"{i+1:3d} {o['fam'][:100]:100s} n {o['n']:5d} /d48 {o['per_day48']:6.1f} | V {V['rule']:19s} pass {o['n_rules_pass_all']:4d} sl {V['slices_all'][1]}/{V['slices_all'][0]} | "
         f"fit {f(V['fit'].get('mean'))} | VAL n {v['n']} {f(v.get('mean'))} med {f(v.get('median'))} win {v.get('win',0):.0%} pull {v.get('pulled',0):.1%} ${V['val_usd_day']:.0f}/d | 24h {f(V['last24'].get('mean'))}")
    s += f" || F {F['rule']} val {f(F['val'].get('mean'))} ${F['val_usd_day']:.0f}/d" if F else " || F none"
    s += f" || W {W['rule']} d7 {f(W['last24'].get('mean'))} n {W['last24']['n']} ${W['last24_usd_day']:.0f}/d" if W else " || W none"
    s += f" | {';'.join(o['known'])[:40]}"
    print(s)
