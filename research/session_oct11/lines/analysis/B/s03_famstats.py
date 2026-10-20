"""Per-family behaviour from pools.jsonl rows (no events): every lc / tok / strict / lc#tok family with >= 10 angle-B launches."""
from common import *
rows = load_rows()
out = []
for g in ("lc", "tok", "lt", "strict"):
    fam = C.defaultdict(list)
    for r in rows: fam[key_of(r, g)].append(r)
    for k, rs in fam.items():
        if len(rs) < 10: continue
        n = len(rs); L = [r["launch"] for r in rs]
        perday = [0] * 7
        for r in rs: perday[day(r)] += 1
        fr = [r for r in rs if r["frb"]]; frb = [r["frb"] for r in fr]
        def inlt(r):
            i = r["frb"]["idx"]; s = r["swaps12"]
            return bool(i is not None and i < len(s) and s[i][10])
        pl = [r for r in rs if r["n_pulls"]]
        n12p = [r for r in rs if r["ev_complete"] and r["outsider12"].get("nf_n")]
        n12r = [r for r in n12p if r["outsider12"].get("nf_reaction")]
        b12p = [r for r in rs if r["ev_complete"] and r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
        b12q = [r for r in b12p if r.get("pull_after_last_buy12") is not None and r["pull_after_last_buy12"] <= 30]
        s = dict(g=g, key=k, n=n, inA=sum(r["in_A"] for r in rs), perday=perday, pd=round(n / 7, 1),
                 quote=top([r["quote"] for r in rs]), feets=top([f"{r['fee']}/{r['tick_spacing']}" for r in rs]),
                 hooks0=sum(r["hooks"] == "0x" + "0" * 40 for r in rs) / n,
                 launch=top([f"{(l['to'] or 'create')[:10]}:{l['selector']}:{l['calldata_len']}" for l in L], 2),
                 value=top([l["value_eth"] for l in L], 2), sqrt_top=topshare([r["sqrt_p0"] for r in rs]),
                 npools_tx=top([l.get("n_pools_in_tx") for l in L], 2), wallets=len({l["from"] for l in L}),
                 liq=sum(1 for r in rs if r["n_adds"]) / n, liq_off=p3([r["liq_off"] for r in rs]),
                 frb_share=len(fr) / n, frb_off=p3([b["off"] for b in frb]), frb_eth=med([b["eth"] for b in frb]),
                 frb_eth_top=topshare([round(b["eth"], 4) for b in frb]), frb_inltx=(sum(inlt(r) for r in fr) / len(fr)) if fr else None,
                 frb_lw=(sum(1 for b in frb if b["eoa_is_launch_wallet"]) / len(fr)) if fr else None,
                 frb_eoa_top=top([b["eoa"] for b in frb], 1, 10), frb_eoas=len({b["eoa"] for b in frb}),
                 frb_also_lc=(sum(1 for b in frb if (b.get("also_in_lc_family") or 0) > 0) / len(fr)) if fr else None,
                 frb_np_med=med([b.get("eoa_npools_bought") for b in frb]),
                 frb_fp=top([f"{(b['to'] or '')[:10]}:{b['sel']}:{b['clen']}" for b in frb], 1), frb_router=top([(b["router"] or "")[:10] for b in frb], 1),
                 pulled=len(pl) / n, pull_off=p3([r["first_pull_off"] for r in pl]), pull_full=(sum(1 for r in pl if r["first_pull_full"]) / len(pl)) if pl else None,
                 pull_before_frb=(sum(1 for r in fr if r.get("pull_before_frb")) / len(fr)) if fr else None,
                 pull_lw=(sum(1 for r in pl if r.get("pull_by_launch_wallet")) / len(pl)) if pl else None,
                 react=f"{len(n12r)}/{len(n12p)}", base=f"{len(b12q)}/{len(b12p)}")
        out.append(s)
json.dump(out, open(os.path.join(D, "famstats.json"), "w"))
def f(x): return "-" if x is None else (f"{x:.0%}" if isinstance(x, float) and x <= 1 else str(x))
with open(os.path.join(D, "famstats.txt"), "w") as o:
    for s in sorted(out, key=lambda s: (s["g"], -s["n"])):
        o.write(f"{s['g']}:{short(s['key'])} n={s['n']} inA={s['inA']} /d {s['perday']} wallets {s['wallets']} | {s['launch']} | value {s['value']} | ptx {s['npools_tx']}\n"
                f"   quote {s['quote']} | fee/ts {s['feets']} | hooks0 {f(s['hooks0'])} | sqrt_top {f(s['sqrt_top'])} | liq {f(s['liq'])} off {s['liq_off']}\n"
                f"   frb {f(s['frb_share'])} off {s['frb_off']} eth {s['frb_eth']} (top size {f(s['frb_eth_top'])}) inLtx {f(s['frb_inltx'])} lw {f(s['frb_lw'])} eoas {s['frb_eoas']} top {s['frb_eoa_top']} alsoLc {f(s['frb_also_lc'])} npools {s['frb_np_med']} fp {s['frb_fp']} router {s['frb_router']}\n"
                f"   pulled {f(s['pulled'])} off {s['pull_off']} full {f(s['pull_full'])} beforeFrb {f(s['pull_before_frb'])} byLW {f(s['pull_lw'])} | react12nf {s['react']} base12 {s['base']}\n")
print(len(out))
