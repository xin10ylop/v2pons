"""robustness around the chosen rules: (1) the vbot 3.0 / 5.0 / C-2 hookless lines over a K x exit table (validation and last 24 h);
(2) the V selection restricted to K >= 2 for families whose V pick is K = 1; (3) the known fixed 3.0 rule (fire +12, hold 60) for reference"""
from gstats import *
rows = {r["pool"]: r for r in load_rows()}
kept = json.load(open(os.path.join(G, "families_kept.json")))
grid = load_grid(0.0058)
def fam(sfx): return [k for k in kept if k.endswith(sfx)][0]
def table(fk, Ks, exits):
    pools = kept[fk]; ts = np.array([rows[p]["launch_ts"] for p in pools]); val = ts >= FIT_END; l24 = ts >= LAST24
    ret, pulled, _ = fam_returns(grid, pools)
    print(f"\n{fk}  (cells: all-7-days mean / validation mean / last-24 h mean, pulled share all days, trades/launches all days)")
    names = [gsim.rule_name(0, i)[3:] for i in exits]
    print("K".rjust(4), " | ".join(n.rjust(30) for n in names))
    for K in Ks:
        ki = gsim.KS.index(K); cells = []
        for i in exits:
            r = ret[:, ki, i]; pu = pulled[:, ki, i]; m = ~np.isnan(r)
            cells.append(f"{np.nanmean(r)*100:+5.1f}/{np.nanmean(r[val])*100:+5.1f}/{np.nanmean(r[l24])*100:+5.1f} p{pu[m].mean()*100:3.0f}% {m.sum()}/{len(r)}")
        print(f"{K:4d}", " | ".join(c.rjust(30) for c in cells))
def ridx(name): return [i for i in range(gsim.NR) if gsim.rule_name(0, i)[3:] == name][0]
ex = [ridx(n) for n in ["hold60", "hold200", "TP20% dl100", "TP20% dl200", "TP50% dl200", "X>=0.1 dl200"]]
table(fam("|1444|10000|200|nohook|ETH|3.0000000"), [2, 10, 12, 16, 20, 30, 40, 60, 80, 100, 150, 200], ex)
table(fam("|1444|10000|200|nohook|ETH|5.0000000"), [2, 8, 12, 20, 40, 80, 150, 200], [ridx(n) for n in ["hold60", "hold200", "TP20% dl200", "TP50% dl200", "X>=0.05 dl200", "X>=0.05 dl40"]])
table(fam("|6276cbbe|196|500|1|nohook|ETH|0.0000000"), [40, 60, 80, 100, 150, 200], [ridx(n) for n in ["hold60", "hold100", "hold200", "TP8% dl100", "TP20% dl200", "X>=0.05 dl100"]])
# (2) V selection with K >= 2
res = {o["fam"]: o for o in json.load(open(os.path.join(G, "g06_results_q0.0058.json")))}
print("\nV selection restricted to K >= 2 (the K = 1 picks):")
for fk, o in res.items():
    if not o["V"] or o["V"]["K"] != 1: continue
    pools = kept[fk]; rs = [rows[p] for p in pools]
    ts = np.array([r["launch_ts"] for r in rs]); fit = ts < FIT_END; val = ~fit; sl = np.array([slice6(t) for t in ts])
    ret, pulled, _ = fam_returns(grid, pools)
    fm, fc, fs = agg(ret, fit); vm, vc, vs = agg(ret, val)
    n3 = np.zeros(fm.shape, int); p3 = np.zeros(fm.shape, int)
    for s in range(28):
        msk = sl == s
        if msk.sum() >= 3:
            m_, c_, _ = agg(ret, msk); n3 += c_ >= 3; p3 += (c_ >= 3) & (m_ > 0)
    ok = (np.arange(18)[:, None] >= 2) & (fc >= 10) & (fm > 0) & (vc >= 5) & (vm > 0)
    clean = ok & (n3 == p3)
    use = clean if clean.any() else ok
    if not use.any(): print(" ", fk[:90], "none"); continue
    a = int(np.argmax(np.where(use, vs, -np.inf))); ki, ri = a // gsim.NR, a % gsim.NR
    v = one(ret[val, ki, ri], pulled[val, ki, ri]); al = one(ret[:, ki, ri], pulled[:, ki, ri])
    print(f"  {fk[:90]:90s} {gsim.rule_name(gsim.KS[ki], ri):20s} {'all slices +' if clean.any() else 'some slice -'} val n {v['n']} mean {v['mean']*100:+.1f}% med {v['median']*100:+.1f}% win {v['win']:.0%} pulled {v['pulled']:.1%} ${v['mean']*0.0058*ETH_USD*v['n']/2:.0f}/day | all {al['mean']*100:+.1f}%")
