"""Step 1: group the non-vbot launches of lc:c873e135|ac9650d8 by exact launch shape (value wei, calldata len, fee, ts, sqrt_p0, mint L,
quote), by token skeleton (fam.tok) and by launch wallet; summarise every group with >= 15 launches. Output groups.json + printed table."""
from common import *
MIN_N = 15
rows = rows_nonvbot(); E = load_ev()
Z40 = "0x" + "0" * 40
for r in rows:
    o = E.get(r["pool"]); L, npos, rng = mint_info(r, o) if o else (None, 0, ())
    r["_mintL"], r["_npos"], r["_rng"] = L, npos, rng
    r["_shape"] = (r["launch"]["value_wei"], r["launch"]["calldata_len"], r["fee"], r["tick_spacing"], r["sqrt_p0"], L, r["quote"], r["hooks"] == Z40)
    r["_day"] = day_of(r)


def fp(f): return f"{f['to'][:10]}:{f['sel']}:{f['clen']}"


def summ(rs):
    n = len(rs); days = C.Counter(r["_day"] for r in rs)
    wal = C.Counter(r["launch"]["from"] for r in rs); non = [r["launch"]["nonce"] for r in rs]
    frb = [r["frb"] for r in rs if r.get("frb")]
    anyb = sum(1 for r in rs if r.get("n_buys")); pulled = [r for r in rs if r.get("n_pulls")]
    o12p = [r for r in rs if r.get("ev_complete") and (r.get("outsider12") or {}).get("nf_n")]
    o12r = [r for r in o12p if r["outsider12"].get("nf_reaction")]
    b12p = [r for r in rs if r.get("ev_complete") and r.get("outsider12") is not None and r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
    b12q = [r for r in b12p if r.get("pull_after_last_buy12") is not None and r["pull_after_last_buy12"] <= 30]
    o12all = [r for r in rs if r.get("ev_complete") and (r.get("outsider12") or {}).get("n")]
    o12allr = [r for r in o12all if r["outsider12"].get("reaction")]
    s = {"n": n, "per_day": [days.get(d, 0) for d in range(7)], "wallets": len(wal), "top_wallet_share": round(wal.most_common(1)[0][1] / n, 3),
         "nonce_p10_50_90": p1050(non), "fresh_le3": round(sum(1 for x in non if x <= 3) / n, 3),
         "shape_top": [[str(k), v] for k, v in C.Counter(r["_shape"] for r in rs).most_common(2)],
         "value_top": C.Counter(f"{r['launch']['value_wei']/1e18:.10g}" for r in rs).most_common(3),
         "clen_top": C.Counter(r["launch"]["calldata_len"] for r in rs).most_common(3), "quote": C.Counter(r["quote"] for r in rs).most_common(3),
         "fee_ts": C.Counter(f"{r['fee']}/{r['tick_spacing']}" for r in rs).most_common(3), "tok_top": [[k[:8], v] for k, v in C.Counter(r["fam"]["tok"] for r in rs).most_common(3)],
         "npos_top": C.Counter(r["_npos"] for r in rs).most_common(2), "n_pools_in_tx_top": C.Counter(r["launch"]["n_pools_in_tx"] for r in rs).most_common(2),
         "any_buy": round(anyb / n, 3), "frb_share": round(len(frb) / n, 3),
         "first_buy_off_p": p1050([r["first_buy_off"] for r in rs if r.get("first_buy_off") is not None]),
         "frb_off_p": p1050([f["off"] for f in frb]), "frb_eth_p": p1050([f["eth"] for f in frb]),
         "frb_eth_top": C.Counter(round(f["eth"], 6) for f in frb).most_common(2),
         "frb_fp_top": C.Counter(fp(f) for f in frb).most_common(3), "frb_eoa_distinct": len({f["eoa"] for f in frb}),
         "frb_eoa_top": [[k[:10], v] for k, v in C.Counter(f["eoa"] for f in frb).most_common(2)],
         "frb_launch_wallet": sum(1 for f in frb if f.get("eoa_is_launch_wallet")),
         "frb_repeat_ge3": sum(1 for f in frb if (f.get("eoa_npools_bought") or 0) >= 3),
         "frb_also_tok": sum(1 for f in frb if (f.get("also_in_tok_family") or 0) > 0), "frb_also_lc": sum(1 for f in frb if (f.get("also_in_lc_family") or 0) > 0),
         "pulled_share": round(len(pulled) / n, 3), "pull_off_p": p1050([r["first_pull_off"] for r in pulled]),
         "pull_before_frb": sum(1 for r in rs if r.get("pull_before_frb")), "pull_no_frb": sum(1 for r in pulled if not r.get("frb")),
         "pull_by_launch_wallet": sum(1 for r in pulled if r.get("pull_by_launch_wallet")),
         "pull_via": C.Counter(f"{r['pulls'][0][2][:10]}:{r['pulls'][0][3]}" for r in pulled).most_common(2),
         "pull_full_share": round(sum(1 for r in pulled if r.get("first_pull_full")) / len(pulled), 3) if pulled else None,
         "o12_reaction": f"{len(o12allr)}/{len(o12all)}", "o12_nf_reaction": f"{len(o12r)}/{len(o12p)}", "baseline12": f"{len(b12q)}/{len(b12p)}"}
    return s


out = {}
for gname, kf in (("shape", lambda r: r["_shape"]), ("tok", lambda r: r["fam"]["tok"]), ("wallet", lambda r: r["launch"]["from"])):
    g = C.defaultdict(list)
    for r in rows: g[kf(r)].append(r)
    big = sorted(((k, v) for k, v in g.items() if len(v) >= MIN_N), key=lambda kv: -len(kv[1]))
    print(f"\n######## grouping {gname}: {len(g)} groups, {len(big)} with >= {MIN_N} launches covering {sum(len(v) for k, v in big)} pools")
    out[gname] = []
    for k, v in big:
        s = summ(v); s["key"] = str(k) if gname != "tok" else k; out[gname].append(s)
        kk = k if gname != "shape" else (f"{k[0]/1e18:.10g}ETH", k[1], k[2], k[3], str(k[4])[:12], str(k[5])[:12], k[6], "nohook" if k[7] else "HOOK")
        print(f"[{gname}] {kk} n={s['n']} /day={s['per_day']} wal={s['wallets']} nonce={s['nonce_p10_50_90']} fresh={s['fresh_le3']} "
              f"val={s['value_top'][:2]} clen={s['clen_top'][:2]} q={s['quote'][:2]} fee={s['fee_ts'][:2]} tok={s['tok_top'][:2]} npos={s['npos_top']} nptx={s['n_pools_in_tx_top']}\n"
              f"    anybuy={s['any_buy']} frb={s['frb_share']} fb_off={s['first_buy_off_p']} frb_off={s['frb_off_p']} frb_eth={s['frb_eth_p']} eth_top={s['frb_eth_top']} "
              f"fp={s['frb_fp_top'][:2]} eoas={s['frb_eoa_distinct']} eoa_top={s['frb_eoa_top']} lw={s['frb_launch_wallet']} rep3={s['frb_repeat_ge3']} alsoTok={s['frb_also_tok']} alsoLc={s['frb_also_lc']}\n"
              f"    pulled={s['pulled_share']} pull_off={s['pull_off_p']} pull<frb={s['pull_before_frb']} pull_no_frb={s['pull_no_frb']} byLW={s['pull_by_launch_wallet']} via={s['pull_via']} full={s['pull_full_share']} "
              f"o12={s['o12_reaction']} o12nf={s['o12_nf_reaction']} base12={s['baseline12']}")
json.dump(out, open(os.path.join(OUT, "groups.json"), "w"), indent=0, default=str)
