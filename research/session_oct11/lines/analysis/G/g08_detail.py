"""the full picture for the top 15 distinct lines (g07_top.json): shape, size, the price path after launch and who moves it, the chosen rule (V)
with fit/validation/all/per-day/per-slice/last-24 h numbers, F and W (out-of-sample) numbers, q = 0.002, the conservative pull rule, the
operator's reaction to outsider buys vs baseline (census definitions, first 12 swaps), engine support, replay reliability"""
from gstats import *
rows = {r["pool"]: r for r in load_rows()}
EV = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
kept = json.load(open(os.path.join(G, "families_kept.json")))
top = json.load(open(os.path.join(G, "g07_top.json")))[:15]
g58 = load_grid(0.0058); g20 = load_grid(0.002)
PM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
OFFS = [1, 2, 5, 10, 20, 40, 80, 150, 200, 300, 400]
ALL_POOLS_SEEN = C.Counter()          # eoa -> pools (first-12 swaps) across all kept rows
for r in rows.values():
    for e in set(s[3] for s in (r["swaps12"] or []) if s[3]): ALL_POOLS_SEEN[e] += 1

def engine(rs):
    sk = C.Counter(shape_key(r) for r in rs).most_common(1)[0][0]
    tgt, sel, clen, fee, ts, hz, quote, val = sk.split("|")
    notes = []
    if quote != "ETH": notes.append(f"small engine change ({quote} quote)")
    if hz == "hook": notes.append("hook risk")
    if tgt != PM or sel != "ac9650d8": notes.append(f"small engine change (new launch decoder {tgt[:10]} {sel} {clen} B)")
    elif clen not in ("1444", "2276"): notes.append(f"small engine change (decoder for the {clen}-byte multicall)")
    return ("tradable today" if not notes else "; ".join(notes)), sk

def price_pct(p, off):
    r = rows[p]; L = r["launch_block"]; s0 = int(r["sqrt_p0"]); sp = None
    for s in EV[p]["sw"]:
        if s[0] <= L + off: sp = s[5]
        else: break
    if sp is None: return 0.0
    x = (s0 / sp) ** 2 if r["quote_side"] == 0 else (sp / s0) ** 2
    return x - 1

out = []
for o in top:
    fk = o["fam"]; pools = kept[fk]; rs = [rows[p] for p in pools]; V = o["V"]
    d = {"fam": fk, "n": len(pools), "per_day48": o["per_day48"], "n24": o["n24"], "known": o["known"], "twins": o["twins"], "tagV": o["tagV"],
         "n_rules_pass_all": o["n_rules_pass_all"], "n_rules_fit_val_pos": o["n_rules_fit_val_pos"], "passing_val_usd_day_median": o.get("passing_val_usd_day_median")}
    d["engine"], d["main_shape"] = engine(rs)
    d["launches_per_day"] = [sum(1 for r in rs if day(r["launch_ts"]) == k) for k in range(7)]
    d["shapes_top"] = C.Counter(shape_key(r) for r in rs).most_common(3)
    d["n_launch_wallets"] = len(set(r["launch"]["from"] for r in rs)); d["nonce_med"] = float(np.median([r["launch"]["nonce"] or 0 for r in rs]))
    d["sqrt0_top_share"] = C.Counter(r["sqrt_p0"] for r in rs).most_common(1)[0][1] / len(rs)
    first_add = []
    for p in pools:
        a = [m[4] for m in EV[p]["mods"] if m[4] > 0]
        first_add.append(a[0] if a else None)
    d["mint_liq_top_share"] = C.Counter(first_add).most_common(1)[0][1] / len(rs)
    d["liq_off_p50_p90"] = [pct([r["liq_off"] for r in rs if r["liq_off"] is not None], q) for q in (0.5, 0.9)]
    # price path (recorded), pools pulled by then excluded
    pp = {}
    for off in OFFS:
        xs = [price_pct(p, off) for p, r in zip(pools, rs) if r["first_pull_off"] is None or r["first_pull_off"] > off]
        pulled_by = sum(1 for r in rs if r["first_pull_off"] is not None and r["first_pull_off"] <= off) / len(rs)
        pp[off] = [pct(xs, 0.1), pct(xs, 0.5), pct(xs, 0.9), pulled_by]
    d["price_path"] = pp
    # who buys early (first 12 swaps, EOAs known)
    lw = cnt_b = 0; rep = C.Counter(); single = 0; fps_single = C.Counter(); tos = C.Counter(); fam_pools = C.Counter()
    for r in rs:
        for e in set(s[3] for s in (r["swaps12"] or []) if s[1] == "B" and s[3]): fam_pools[e] += 1
    for r in rs:
        for s in (r["swaps12"] or []):
            if s[1] != "B" or s[2] < 0.0001: continue
            cnt_b += 1; tos[(s[4] or "")[:10]] += 1
            if s[3] == r["launch"]["from"]: lw += 1
            elif fam_pools[s[3]] >= 5: rep[s[3][:10]] += 1
            elif ALL_POOLS_SEEN[s[3]] < 3:
                single += 1; fps_single[f"{(s[4] or '')[:10]}:{s[5]}:{s[6]}"] += 1
    d["early_buys12"] = {"n": cnt_b, "launch_wallet": lw / max(cnt_b, 1), "repeat_wallets(>=5 pools)": sum(rep.values()) / max(cnt_b, 1),
                         "n_repeat_wallets": len(rep), "top_repeat": rep.most_common(3), "single_use": single / max(cnt_b, 1),
                         "single_use_top_fp": fps_single.most_common(2), "to_top": tos.most_common(3)}
    frb = [r["frb"] for r in rs if r.get("frb")]
    d["frb"] = {"share": len(frb) / len(rs), "off_p10_50_90": [pct([f["off"] for f in frb], q) for q in (0.1, 0.5, 0.9)],
                "eth_med": pct([f["eth"] for f in frb], 0.5), "by_launch_wallet": sum(1 for f in frb if f.get("eoa_is_launch_wallet")) / max(1, len(frb)),
                "to_top": C.Counter((f.get("to") or "")[:10] for f in frb).most_common(2), "eoa_top": C.Counter((f.get("eoa") or "")[:10] for f in frb).most_common(2),
                "eoa_npools_bought_med": pct([f.get("eoa_npools_bought") for f in frb], 0.5)}
    # in the V rule's hold windows: buy ETH by the Swap event's sender (the router/contract calling the PoolManager)
    ret, pulled, so = fam_returns(g58, pools)
    ki, ri = V["ki"], V["ri"]; K = V["K"]
    byr = C.Counter(); nb = 0; szs = []
    for j, p in enumerate(pools):
        if np.isnan(ret[j, ki, ri]): continue
        L = rows[p]["launch_block"]; a, b = L + K, L + int(so[j, ki, ri])
        for s in EV[p]["sw"]:
            if a <= s[0] < b and s[2] and not s[8].startswith(OUR_RELAY):
                e = (s[3] / (1e6 * ETH_USD) if rows[p]["quote"] == "USDG" else s[3] / 1e18 / (ETH_USD if rows[p]["quote"] == "USDG2" else 1))
                byr[s[8][:10]] += e; nb += 1; szs.append(e)
    tot = sum(byr.values()) or 1
    d["hold_window_buys"] = {"n_buys": nb, "eth": tot, "per_trade_eth": tot / max(1, (~np.isnan(ret[:, ki, ri])).sum()), "size_med": pct(szs, 0.5),
                             "by_sender": [[k, v / tot] for k, v in byr.most_common(4)]}
    # conservative pull rule and q = 0.002 for the same rule
    rc, pc, _ = fam_returns(g58, pools, conservative=True)
    d["V_conservative_pull"] = one(rc[:, ki, ri], pc[:, ki, ri])
    if all(p in g20["ix"] for p in pools):
        r2, p2, _ = fam_returns(g20, pools)
        ts = np.array([r["launch_ts"] for r in rs]); val = ts >= FIT_END
        d["V_q0.002_all"] = one(r2[:, ki, ri], p2[:, ki, ri]); d["V_q0.002_val"] = one(r2[val, ki, ri], p2[val, ki, ri])
        d["V_q0.002_val_usd_day"] = d["V_q0.002_val"]["mean"] * 0.002 * ETH_USD * d["V_q0.002_val"]["n"] / 2 if d["V_q0.002_val"]["n"] else None
    # reaction (census definitions, first 12 swaps)
    n12p = [r for r in rs if (r.get("outsider12") or {}).get("nf_n")]
    n12r = [r for r in n12p if r["outsider12"].get("nf_reaction")]
    b12p = [r for r in rs if r.get("outsider12") is not None and r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
    b12q = [r for r in b12p if r.get("pull_after_last_buy12") is not None and r["pull_after_last_buy12"] <= 30]
    po = [r["first_pull_off"] for r in rs if r["first_pull_off"] is not None]
    d["reaction"] = {"outsider12_nf": [len(n12r), len(n12p)], "baseline12": [len(b12q), len(b12p)],
                     "pulled_share_3000": len(po) / len(rs), "pull_off_p10_50_90": [pct(po, q) for q in (0.1, 0.5, 0.9)],
                     "pull_by_launch_wallet": sum(1 for r in rs if r.get("pull_by_launch_wallet")) / max(1, len(po)),
                     "pull_before_frb": sum(1 for r in rs if r.get("frb") and r["first_pull_off"] is not None and r["first_pull_off"] < r["frb"]["off"])}
    # replay reliability: cumulative path error on every pool of the family
    errs = []
    import gsim2
    bad = 0
    for p in pools:
        e, _ = gsim2.PoolSim(rows[p], EV[p]).validate(EV[p]); errs += e
        if e and max(e) > 1e-6: bad += 1
    d["replay_err"] = {"swaps": len(errs), "p50": pct(errs, 0.5), "p99": pct(errs, 0.99), "pools_with_err_gt_1e-6": bad}
    d["V"] = V; d["F"] = o["F"]; d["W"] = o["W"]
    out.append(d)
json.dump(out, open(os.path.join(G, "g08_detail.json"), "w"), indent=1, default=str)

def P(x): return "-" if x is None else f"{x*100:+.1f}%"
for i, d in enumerate(out):
    V = d["V"]; v = V["val"]; a = V["all"]
    print(f"\n#{i+1} {d['fam']}\n  known: {d['known']} twins: {d['twins']}  engine: {d['engine']}")
    print(f"  shape: {d['main_shape']}  shapes_top: {[(k[:60], n) for k, n in d['shapes_top']]}")
    print(f"  size: n {d['n']}, per day (last 48 h) {d['per_day48']}, by day {d['launches_per_day']}, launch wallets {d['n_launch_wallets']} nonce med {d['nonce_med']}, sqrt0 same {d['sqrt0_top_share']:.0%}, mint liq same {d['mint_liq_top_share']:.0%}, liq_off p50/p90 {d['liq_off_p50_p90']}")
    print("  price path p10/p50/p90 (pulled-by share): " + "; ".join(f"+{k}: {P(x[0])}/{P(x[1])}/{P(x[2])} ({x[3]:.0%})" for k, x in d["price_path"].items()))
    e = d["early_buys12"]
    print(f"  early buys (first 12 swaps, >= 0.0001 ETH): n {e['n']}, launch wallet {e['launch_wallet']:.0%}, repeat wallets (>=5 pools) {e['repeat_wallets(>=5 pools)']:.0%} ({e['n_repeat_wallets']} wallets, top {e['top_repeat']}), single-use {e['single_use']:.0%} (top fps {e['single_use_top_fp']}), to {e['to_top']}")
    f = d["frb"]
    print(f"  first real buy: in {f['share']:.0%}, off p10/50/90 {f['off_p10_50_90']}, eth med {f['eth_med']}, by launch wallet {f['by_launch_wallet']:.0%}, to {f['to_top']}, eoa {f['eoa_top']}, eoa pools bought med {f['eoa_npools_bought_med']}")
    h = d["hold_window_buys"]
    print(f"  in our hold windows: {h['n_buys']} buys, {h['eth']:.2f} ETH ({h['per_trade_eth']:.3f} per trade, size med {h['size_med']}), by sender {[(k, round(s, 3)) for k, s in h['by_sender']]}")
    print(f"  V rule {V['rule']} ({d['tagV']}; {d['n_rules_pass_all']} rules pass every slice, {d['n_rules_fit_val_pos']} positive on fit and validation; median validated $/day of the passing rules {d['passing_val_usd_day_median']})")
    for nm in ("fit", "val", "all", "last24"):
        x = V[nm]
        if x["n"]: print(f"    {nm:6s} n {x['n']}/{x['launches']} mean {P(x['mean'])} med {P(x['median'])} win {x['win']:.0%} worst {P(x['worst'])} pulled {x['pulled']:.1%} ${x['usd_per_trade']:.2f}/trade")
    print(f"    validated $/day {V['val_usd_day']:.1f}; last-24 h $/day {V['last24_usd_day']:.1f}; slices all {V['slices_all'][1]}/{V['slices_all'][0]} fit {V['slices_fit'][1]}/{V['slices_fit'][0]} val {V['slices_val'][1]}/{V['slices_val'][0]}")
    print("    per day mean (n): " + " ".join(f"{P(x.get('mean'))}({x['n']})" for x in V["per_day"]))
    print("    6-h slices (n, mean): " + " ".join(f"{s[1]}:{'-' if s[2] is None else f'{s[2]*100:+.0f}'}" for s in V["slices"]))
    k0 = V["k0_bound"]; print(f"    K=0 bound (same exit): n {k0['n']} mean {P(k0.get('mean'))}; conservative pull (pull in the sell block = loss): mean {P(d['V_conservative_pull'].get('mean'))} pulled {d['V_conservative_pull'].get('pulled', 0):.1%}")
    if "V_q0.002_val" in d:
        print(f"    q 0.002: all n {d['V_q0.002_all']['n']} mean {P(d['V_q0.002_all'].get('mean'))}; val mean {P(d['V_q0.002_val'].get('mean'))} med {P(d['V_q0.002_val'].get('median'))} ${d['V_q0.002_val_usd_day']:.1f}/day")
    F, W = d["F"], d["W"]
    print(f"  F (fit-only pick) {F['rule'] if F else None}: val {P(F['val'].get('mean')) if F else '-'} n {F['val']['n'] if F else 0} ${F['val_usd_day'] if F else 0:.1f}/day | W (picked on days 1-6) {W['rule'] if W else None}: last 24 h {P(W['last24'].get('mean')) if W else '-'} n {W['last24']['n'] if W else 0} ${W['last24_usd_day'] if W else 0:.1f}/day")
    rr = d["reaction"]
    print(f"  reaction: outsider12 (shared fps excluded) pulled <= 30 blocks after: {rr['outsider12_nf'][0]}/{rr['outsider12_nf'][1]} vs baseline {rr['baseline12'][0]}/{rr['baseline12'][1]}; pulled in 3,000 blocks {rr['pulled_share_3000']:.0%} at p10/50/90 {rr['pull_off_p10_50_90']}, by launch wallet {rr['pull_by_launch_wallet']:.0%}, pulls before the first real buy {rr['pull_before_frb']}")
    print(f"  replay: {d['replay_err']}")
