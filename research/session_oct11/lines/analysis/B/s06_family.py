"""Per active family: launch shape, the first real buy (offset, size, who), the wave after it, pulls, and the brief's replays
(front a=2 / sell into their buy / fixed holds, delayed front, a fixed-offset delayed front, follow a=frb+2 with b=a+20/a+60 and the
oracle exit), for q = 0.0058 and 0.002 ETH, by launch day. Output: fam_results.json + fam_results.txt."""
import pickle, sys
from common import *
from replay import Pool, to_eth, GAS_ETH
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
FS = {s["key"]: s for s in json.load(open(os.path.join(D, "famstats.json"))) if s["g"] == "lt"}
ONLY = set(sys.argv[1:])
byfam = C.defaultdict(list)
for pid, k in FAM.items(): byfam[k].append(pid)
# the family's core shape: its most common (quote, fee, tick spacing, hook-or-not) among its launches, as its own row "<key>@core"
def shape_of(r): return (r["quote"], r["fee"], r["tick_spacing"], r["hooks"] == "0x" + "0" * 40)
for k in list(byfam):
    ps = byfam[k]; c = C.Counter(shape_of(rows[p]) for p in ps); top_shape, m = c.most_common(1)[0]
    if m < len(ps): byfam[k + "@core"] = [p for p in ps if shape_of(rows[p]) == top_shape]
QS = (0.0058, 0.002)

def summ(xs):
    """xs = [(ret, pulled, day)] -> stats"""
    if not xs: return None
    r = [x[0] for x in xs]
    o = {"n": len(xs), "mean": sum(r) / len(r), "med": pct(r, .5), "win": sum(1 for v in r if v > 0) / len(r), "worst": min(r),
         "pulled": sum(1 for x in xs if x[1]) / len(xs), "byday": {}}
    for d in range(7):
        rd = [x for x in xs if x[2] == d]
        if rd: o["byday"][d] = (len(rd), sum(x[0] for x in rd) / len(rd), sum(1 for x in rd if x[1]) / len(rd))
    return o

def price_move(P, s_before, s_after):
    return (s_before / s_after) ** 2 - 1 if P.qs == 0 else (s_after / s_before) ** 2 - 1

out = {}
for k, pids in sorted(byfam.items(), key=lambda kv: -len(kv[1])):
    if ONLY and short(k) not in ONLY and k not in ONLY: continue
    rs = [rows[p] for p in pids]; n = len(rs)
    P = {p: Pool(rows[p], E[p]) for p in pids}
    # ---- launch shape
    first_add = []
    for p in pids:
        adds = [m for m in P[p].mods if m[4] > 0]
        first_add.append(adds[0][4] if adds else None)
    shape = {"to": top([(r["launch"]["to"] or "create")[:12] for r in rs], 3), "target_hash": top([r["fam"]["lc"][:10] for r in rs], 2),
             "selector": top([r["launch"]["selector"] for r in rs], 2), "clen": top([r["launch"]["calldata_len"] for r in rs], 4),
             "value": top([r["launch"]["value_eth"] for r in rs], 4), "fee_ts": top([f"{r['fee']}/{r['tick_spacing']}" for r in rs], 3),
             "hooks": top([r["hooks"][:12] for r in rs], 3), "quote": top([r["quote"] for r in rs], 3),
             "sqrt0_top": topshare([r["sqrt_p0"] for r in rs]), "liq_top": topshare([x for x in first_add if x]),
             "liq_off": p3([r["liq_off"] for r in rs]), "wallets": len({r["launch"]["from"] for r in rs}),
             "perday": [sum(1 for r in rs if day(r) == d) for d in range(7)], "n_pools_in_tx": top([r["launch"]["n_pools_in_tx"] for r in rs], 2)}
    # ---- first real buy
    fr = [r for r in rs if r["frb"]]
    frbinfo = {"share": len(fr) / n, "off": p3([r["frb"]["off"] for r in fr]), "eth_med": med([r["frb"]["eth"] for r in fr]),
               "eth_p": p3([r["frb"]["eth"] for r in fr]), "size_top": topshare([round(r["frb"]["eth"], 4) for r in fr]),
               "eoa_top": top([r["frb"]["eoa"][:10] for r in fr], 2), "eoas": len({r["frb"]["eoa"] for r in fr}),
               "npools_med": med([r["frb"].get("eoa_npools_bought") for r in fr]),
               "also_lc": (sum(1 for r in fr if (r["frb"].get("also_in_lc_family") or 0) > 0) / len(fr)) if fr else None,
               "fp": top([f"{(r['frb']['to'] or '')[:10]}:{r['frb']['sel']}:{r['frb']['clen']}" for r in fr], 2),
               "lw": (sum(1 for r in fr if r["frb"]["eoa_is_launch_wallet"]) / len(fr)) if fr else None}
    inl, mv, mv_launch, wave = [], [], [], {20: [], 60: [], 200: []}
    matched = 0
    for r in fr:
        p = P[r["pool"]]; b = r["frb"]; i = b["idx"]
        if i is None or i >= len(p.sw) or p.sw[i][0] != r["launch_block"] + b["off"] or not p.sw[i][2]: continue
        matched += 1; s = p.sw[i]
        s_before = p.sw[i - 1][5] if i > 0 else p.sqrt0
        mv.append(price_move(p, s_before, s[5]))
        inl.append(r["swaps12"][i][10] if i < len(r["swaps12"]) else False)
        if b["off"] == 0:
            mv_launch.append(price_move(p, p.sqrt0, max((x for x in p.sw if x[0] == r["launch_block"]), key=lambda x: x[1])[5]))
        for W in wave:
            later = [x for x in p.sw[i + 1:] if x[0] <= s[0] + W and x[2]]
            wave[W].append((len(later), sum(to_eth(x[8], p.quote) for x in later), sum(1 for x in later if to_eth(x[8], p.quote) >= 0.005)))
    frbinfo.update({"matched": matched, "in_launch_tx": (sum(inl) / len(inl)) if inl else None, "move": p3([100 * x for x in mv]),
                    "launch_tx_move": p3([100 * x for x in mv_launch]) if mv_launch else None})
    wv = {W: {"n_med": med([x[0] for x in v]), "n_mean": (sum(x[0] for x in v) / len(v)) if v else None, "eth_med": med([x[1] for x in v]),
              "eth_mean": (sum(x[1] for x in v) / len(v)) if v else None, "real_any": (sum(1 for x in v if x[2] > 0) / len(v)) if v else None} for W, v in wave.items()}
    # ---- pulls
    pl = [r for r in rs if r["n_pulls"]]
    pulls = {"share": len(pl) / n, "off": p3([r["first_pull_off"] for r in pl]), "frac_med": med([r["pulls"][0][5] for r in pl]),
             "full": (sum(1 for r in pl if r["first_pull_full"]) / len(pl)) if pl else None,
             "before_frb": (sum(1 for r in fr if r.get("pull_before_frb")) / len(fr)) if fr else None,
             "pull_minus_frb": p3([r["pull_minus_frb"] for r in fr if r.get("pull_minus_frb") is not None]),
             "by_lw": (sum(1 for r in pl if r["pulls"][0][1] == r["launch"]["from"]) / len(pl)) if pl else None,
             "via": top([f"{(r['pulls'][0][2] or '')[:10]}:{r['pulls'][0][3]}" for r in pl], 2),
             "react12nf": FS.get(k.split("@")[0], {}).get("react"), "base12": FS.get(k.split("@")[0], {}).get("base")}
    # ---- replays
    offs = [r["frb"]["off"] for r in fr]
    p10 = pct(offs, .1) if offs else None; p90 = pct(offs, .9) if offs else None
    rep = {}
    for q in QS:
        R = C.defaultdict(list); skips = C.Counter()
        for r in rs:
            p = P[r["pool"]]; d = day(r); lo = r["liq_off"] or 0
            a_eff = max(2, lo + 2)
            fo = r["frb"]["off"] if r["frb"] else None
            def add(name, a, b, extra=None):
                if b <= a: skips[name + ":b<=a"] += 1; return
                x = p.replay(a, b, q, oracle_to=extra)
                if "skip" in x: skips[name + ":" + x["skip"]] += 1; return
                R[name].append((x["ret"], x["pulled"], d))
                if extra: R[name + "_oracle"].append(((x["best"] if x["best"] is not None else x["ret"]), x["pulled"] and x["best"] is None, d))
            # front, a = 2 (or 2 blocks after the first liquidity add)
            if fo is not None and fo < a_eff: skips["front:late"] += 1
            else:
                dl = max(10, int(p90 + 1 - a_eff)) if p90 is not None else 60
                add("front_into", a_eff, (fo + 1) if fo is not None else a_eff + dl)
                for h in (8, 18, 38): add(f"front_h{h}", a_eff, a_eff + h)
            # fixed-offset delayed front: fire at the family's p10 - 2, sell into their buy (or hold 60 when none)
            if p10 is not None and p10 - 2 >= a_eff:
                af = int(p10 - 2)
                if fo is not None and fo < af: skips["fixfront:late"] += 1
                else:
                    add("fixfront_into", af, (fo + 1) if fo is not None else af + 60)
                    add("fixfront_h60", af, af + 60)
            if fo is not None:
                for kk in (2, 3, 4, 5, 6):
                    if fo - kk >= a_eff: add(f"delay_k{kk}", fo - kk, fo - kk + 60)
                a = fo + 2
                add("follow_h20", a, a + 20, extra=fo + 201)
                add("follow_h60", a, a + 60)
        rep[q] = {"rules": {nm: summ(v) for nm, v in R.items()}, "skips": dict(skips)}
    out[k] = {"n": n, "shape": shape, "frb": frbinfo, "wave": wv, "pulls": pulls, "replay": rep, "fixfront_a": (int(p10 - 2) if p10 is not None else None)}
    print(short(k), n, "done", flush=True)
json.dump(out, open(os.path.join(D, "fam_results.json" if not ONLY else "fam_results_part.json"), "w"), default=str)
