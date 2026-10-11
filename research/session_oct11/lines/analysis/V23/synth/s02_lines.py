"""Synthesizer step 2: the 9 surviving candidate keys collapse into 4 distinct lines; each line's rule recomputed here with the grid analysts'
integer replays (G3/opus/v3sim.V3Pool.replay, G2/o55/v2sim.PoolSim.roundtrip; imported read-only, no bytecode written), at the $15 stake
(q 0.0058 ETH) and at the owner's $5 probe (q 0.00195 ETH). Returns are net of the $0.02 gas; a pull (Burn) in a block <= the sell block is
-100% minus gas; no trade when the pull is at or before the buy block - 2. -> s02_lines.out, s02_lines.json"""
import sys, os, json, pickle, statistics as S, collections as C
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
AN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis"
sys.path.insert(0, AN + "/G3/opus"); import v3sim
sys.path.insert(0, AN + "/G2/o55"); from v2sim import PoolSim
FROM_TS = 1791121962; END_TS = FROM_TS + 7 * 86400; FIT_END = FROM_TS + 5 * 86400; LAST24 = END_TS - 86400
ETH_USD = 2570.0; GAS = 0.02
day = lambda ts: min(6, max(0, int((ts - FROM_TS) // 86400))); sl6 = lambda ts: min(27, max(0, int((ts - FROM_TS) // 21600)))
F3 = json.load(open(AN + "/G3/opus/families.json")); F2 = json.load(open(AN + "/G2/o55/families_kept.json"))
R3 = {r["pool"]: r for r in pickle.load(open(AN + "/G3/opus/v3rows.pkl", "rb"))}; E3 = pickle.load(open(AN + "/G3/opus/ev.pkl", "rb"))
R2 = {r["pool"]: r for r in pickle.load(open(AN + "/G2/o55/v2rows.pkl", "rb"))}; E2 = pickle.load(open(AN + "/G2/o55/ev.pkl", "rb"))
K_CROWD = "shape=0x73991a25c818bf1f1128deaab1492d45638de0d3|ac9650d8|836|100|1|WETH|0.0000000"
K_D4 = "tok=tok:d4e7eae43daa222b2f8e97be53376a3d434d42e2871c651d5e3c69dba24d672e"; K_LCAC = "lc=0a493d1a|ac9650d8"
K_356 = "shapecode=89885b75fd29af13|d27d1e00|356|100|1|WETH|0.0000000"; K_LC89 = "lc=89885b75|d27d1e00"
K_97 = "tok=tok:97c7ba1b0d3f2de327f8c7b22abf2c270505eaa878bc2ae431fc8ffc532271d0"
K_FLEET = "tok:0f34e3b5f0599dd75dae3f5228a1ef936f4b3b483718bc6ce17002d24581092d"
SH = "shape:0x89e5db8b5aa49aa85ac63f691524311aeb649eba|f305d719|196|3000|None|WETH|"
K_70 = "tok:70adce63e2b26b9350075e6934c9204c09dd0534884b162b9386ff9bff162a22"
L = []; OUT = {}
def P(s=""): L.append(s); print(s)
# ---- overlaps (which keys are the same line)
s = {k: set(v) for k, v in F3.items()}; s2 = {k: set(v) for k, v in F2.items()}
P("OVERLAPS")
P(f"  crowd 836-B shape {len(s[K_CROWD])}; tok d4e7eae4 {len(s[K_D4])}; lc ac9650d8 {len(s[K_LCAC])}; shape & tok {len(s[K_CROWD] & s[K_D4])}; shape within lc {len(s[K_CROWD] & s[K_LCAC])}; "
  f"tok within lc {len(s[K_D4] & s[K_LCAC])}")
P(f"  356-B shapecode {len(s[K_356])}; lc 89885b75 {len(s[K_LC89])}; tok 97c7ba1b {len(s[K_97])}; 356 within lc {len(s[K_356] & s[K_LC89])}; 356 & tok97 {len(s[K_356] & s[K_97])}; "
  f"tok97 within lc {len(s[K_97] & s[K_LC89])}")
f1 = s2[SH + "1.0000000"]; v40 = s2[SH + "50.0900000"] | s2[SH + "40.0900000"] | s2[SH + "40.5900000"]
P(f"  V2 fleet tok {len(s2[K_FLEET])}; 1.0-ETH shape {len(f1)}; fleet within shape {len(s2[K_FLEET] & f1)}")
P(f"  V2 tok 70adce63 {len(s2[K_70])}; value >= 40 shapes (50.09/40.09/40.59) {len(v40)}, within tok {len(v40 & s2[K_70])}; 30.09 {len(s2[SH + '30.0900000'])}")
# ---- replays
def v3run(pools, a, b, q):
    xs = []
    for p in pools:
        r = R3[p]; sim = v3sim.V3Pool(r, E3[p]); A = sim.anchor + a
        if sim.pull_bn is not None and sim.pull_bn <= A - 2: continue
        x = sim.replay(A, sim.anchor + b, q)
        if x is None: continue
        g = GAS / ETH_USD / q
        xs.append({"p": p, "ts": r["launch_ts"], "ret": (-1.0 - g) if x["pulled"] else x["ret_nopull"] - g, "pulled": x["pulled"], "q": q})
    return xs
def v2run(pools, a, b, q):
    xs = []
    for p in pools:
        r = R2[p]; o = E2[p]; ps = PoolSim(o["ev"], o["lb"], o["ev_to"], (997, 1000), {}, None)
        lb = r["launch_block"]
        if ps.pull_bn is not None and ps.pull_bn <= lb + a - 2: continue
        x = ps.roundtrip(lb + a, lb + b, q)
        if x is None: continue
        g = GAS / ETH_USD / q
        xs.append({"p": p, "ts": r["launch_ts"], "ret": (-1.0 - g) if x["pulled"] else x["ret"], "pulled": x["pulled"], "q": q})
    return xs
def stats(xs, lab):
    r = [x["ret"] for x in xs]; q = xs[0]["q"]; usd = q * ETH_USD
    m = S.mean(r); val = [x["ret"] for x in xs if x["ts"] >= FIT_END]; l24 = [x["ret"] for x in xs if x["ts"] >= LAST24]
    dd = C.defaultdict(list); ss = C.defaultdict(list)
    for x in xs: dd[day(x["ts"])].append(x["ret"]); ss[sl6(x["ts"])].append(x["ret"])
    sq = [v for v in ss.values() if len(v) >= 3]; srt = sorted(r, reverse=True); tot = sum(r)
    o = {"n": len(r), "mean": m, "median": S.median(r), "win": sum(1 for a in r if a > 0) / len(r), "worst": min(r), "pulled": sum(x["pulled"] for x in xs) / len(xs),
         "usd_trade": m * usd, "usd_day7": tot * usd / 7, "val_n": len(val), "val_mean": S.mean(val) if val else None, "val_usd_day": sum(val) * usd / 2,
         "l24_n": len(l24), "l24_mean": S.mean(l24) if l24 else None, "l24_usd": sum(l24) * usd, "days": [S.mean(dd[d]) if dd[d] else None for d in range(7)],
         "slices": f"{sum(1 for v in sq if S.mean(v) > 0)}/{len(sq)}", "top10pct_share": sum(srt[:max(1, len(r) // 10)]) / tot if tot > 0 else None,
         "mean_wo_top10": S.mean(srt[10:]), "breakeven_pull": m / (m + 1 + GAS / ETH_USD / q)}
    P(f"  {lab}: n {o['n']} mean {m*100:+.2f}% median {o['median']*100:+.3f}% win {o['win']*100:.1f}% worst {o['worst']*100:+.1f}% pulled {o['pulled']*100:.2f}% "
      f"${o['usd_trade']:.3f}/trade ${o['usd_day7']:.1f}/day(7d)")
    P(f"      days 6-7 n {o['val_n']} {o['val_mean']*100:+.2f}% ${o['val_usd_day']:.1f}/day | last 24 h n {o['l24_n']} {o['l24_mean']*100:+.2f}% ${o['l24_usd']:.1f} | slices {o['slices']} | "
      f"by day " + " ".join("-" if v is None else f"{v*100:+.1f}" for v in o["days"]))
    P(f"      top 10% of trades = {o['top10pct_share']*100:.0f}% of the return; mean without the best 10 {o['mean_wo_top10']*100:+.2f}%; break-even extra pull share {o['breakeven_pull']*100:.2f}%")
    return o
Q15, Q5 = 0.0058, round(5 / ETH_USD, 6)
LINES = [("V3 crowd 836-B shape, K20 sell +80", "v3", sorted(s[K_CROWD]), 20, 80),
         ("V3 crowd 836-B shape, buy +2 sell +80", "v3", sorted(s[K_CROWD]), 2, 80),
         ("V3 356-B d27d1e00 value 0, K60 sell +260", "v3", sorted(s[K_356]), 60, 260),
         ("V2 fleet tok 0f34e3b5, buy +20 sell +80", "v2", sorted(s2[K_FLEET]), 20, 80),
         ("V2 tok 70adce63 value >= 40 ETH, buy +150 sell +250", "v2", sorted(v40 & s2[K_70]), 150, 250)]
for lab, dex, pools, a, b in LINES:
    P(f"\n{lab} ({len(pools)} launches)")
    for q in (Q15, Q5):
        xs = (v3run if dex == "v3" else v2run)(pools, a, b, q)
        OUT[f"{lab} q{q}"] = stats(xs, f"q {q} (${q*ETH_USD:.2f})")
        if dex == "v3" and "356" in lab and q == Q15: T356 = xs
        if dex == "v3" and "K20" in lab and q == Q15: TCR = xs
# ---- crowd line: how often the crowd's first real buy (>= 0.005 ETH) lands by +80, by day (the census side of the forward comparison)
P("\nV3 crowd 836-B: first real buy (>= 0.005 ETH) at or before +80, by launch day (census)")
byd = C.defaultdict(lambda: [0, 0])
for p in s[K_CROWD]:
    r = R3[p]; f = r.get("frb"); d = day(r["launch_ts"]); byd[d][1] += 1
    if f and f["off"] <= 80: byd[d][0] += 1
tot = [sum(v[0] for v in byd.values()), sum(v[1] for v in byd.values())]
P("  " + " ".join(f"d{d+1} {byd[d][0]}/{byd[d][1]} ({byd[d][0]/byd[d][1]*100:.0f}%)" for d in range(7)) + f" | all {tot[0]}/{tot[1]} ({tot[0]/tot[1]*100:.1f}%)")
OUT["crowd_frb80_census"] = {"by_day": {d: byd[d] for d in range(7)}, "all": tot}
cr = {x["p"]: x["ret"] for x in TCR}
w80 = [cr[p] for p in s[K_CROWD] if p in cr and R3[p].get("frb") and R3[p]["frb"]["off"] <= 80]
n80 = [cr[p] for p in s[K_CROWD] if p in cr and not (R3[p].get("frb") and R3[p]["frb"]["off"] <= 80)]
P(f"  K20/+80 at $15: pools with the first real buy by +80 n {len(w80)} mean {S.mean(w80)*100:+.2f}% | the rest n {len(n80)} mean {S.mean(n80)*100:+.2f}% median {S.median(n80)*100:+.3f}%")
OUT["crowd_split_frb80"] = {"with": [len(w80), S.mean(w80)], "without": [len(n80), S.mean(n80), S.median(n80)]}
pickle.dump({"T356": T356, "TCR": TCR}, open(os.path.join(HERE, "s02_trades.pkl"), "wb"))
json.dump(OUT, open(os.path.join(HERE, "s02_lines.json"), "w"), indent=1, default=str)
open(os.path.join(HERE, "s02_lines.out"), "w").write("\n".join(L) + "\n")
