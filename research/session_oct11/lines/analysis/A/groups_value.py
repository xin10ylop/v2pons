"""The engine's view: group by (msg.value wei, calldata len, fee, tick spacing, quote, hook-free) ignoring launch price/liquidity, and
report how many distinct (sqrt_p0, mint L) each has; also by msg.value alone for value > 0. Groups with >= 15 launches."""
from common import *
import groups as G   # reuses rows with _shape, _mintL and summ()
rows = G.rows
out = {}
for gname, kf in (("value_shape", lambda r: (r["launch"]["value_wei"], r["launch"]["calldata_len"], r["fee"], r["tick_spacing"], r["quote"], r["hooks"] == G.Z40)),
                  ("value_only", lambda r: r["launch"]["value_wei"])):
    g = C.defaultdict(list)
    for r in rows: g[kf(r)].append(r)
    big = sorted(((k, v) for k, v in g.items() if len(v) >= 15), key=lambda kv: -len(kv[1]))
    print(f"\n######## {gname}: {len(big)} groups >= 15 covering {sum(len(v) for k, v in big)}")
    out[gname] = []
    for k, v in big:
        s = G.summ(v); s["key"] = str(k); s["n_price_liq"] = len({(r["sqrt_p0"], r["_mintL"]) for r in v}); s["n_sqrtp"] = len({r["sqrt_p0"] for r in v}); s["n_L"] = len({r["_mintL"] for r in v})
        s["n_tok"] = len({r["fam"]["tok"] for r in v}); out[gname].append(s)
        kk = (f"{k[0]/1e18:.10g}ETH",) + tuple(k[1:]) if isinstance(k, tuple) else f"{k/1e18:.10g}ETH"
        print(f"[{gname}] {kk} n={s['n']} /day={s['per_day']} wal={s['wallets']} nonce={s['nonce_p10_50_90']} fresh={s['fresh_le3']} distinct(sqrt,L)={s['n_price_liq']} sqrt={s['n_sqrtp']} L={s['n_L']} tokfams={s['n_tok']} tok={s['tok_top'][:2]} clen={s['clen_top'][:2]} q={s['quote'][:2]} fee={s['fee_ts'][:2]} kfp={C.Counter(r['known_fp'] for r in v).most_common(2)}\n"
              f"    anybuy={s['any_buy']} frb={s['frb_share']} fb_off={s['first_buy_off_p']} frb_off={s['frb_off_p']} frb_eth={s['frb_eth_p']} eth_top={s['frb_eth_top']} fp={s['frb_fp_top'][:2]} eoas={s['frb_eoa_distinct']} eoa_top={s['frb_eoa_top']} rep3={s['frb_repeat_ge3']} alsoLc={s['frb_also_lc']}\n"
              f"    pulled={s['pulled_share']} pull_off={s['pull_off_p']} pull<frb={s['pull_before_frb']} pull_no_frb={s['pull_no_frb']} byLW={s['pull_by_launch_wallet']} via={s['pull_via'][:1]} o12={s['o12_reaction']} o12nf={s['o12_nf_reaction']} base12={s['baseline12']}")
json.dump(out, open(os.path.join(OUT, "groups_value.json"), "w"), indent=0, default=str)
