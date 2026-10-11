from gstats import *
rows = {r["pool"]: r for r in load_rows()}
EV = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
kept = json.load(open(os.path.join(G, "families_kept.json")))
grid = load_grid(0.0058)
for fk, rule in [("tok=tok:d4e7eae4", "K150 TP20% dl200"), ("shape=0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|hook|ETH", "K100 hold100"), ("tok=tok:037449b1", "K200 TP50% dl200")]:
    k = [x for x in kept if x.startswith(fk)][0]; pools = kept[k]
    ret, pulled, so = fam_returns(grid, pools)
    ki = gsim.KS.index(int(rule.split()[0][1:])); ri = [i for i in range(gsim.NR) if gsim.rule_name(gsim.KS[ki], i) == rule][0]
    r = ret[:, ki, ri]; o = np.argsort(np.nan_to_num(r, nan=-9))[::-1]
    print(k[:80], rule, "n", (~np.isnan(r)).sum(), "mean", np.nanmean(r), "mean without top 1%:", np.nanmean(np.sort(r[~np.isnan(r)])[:-max(1, int(0.01*(~np.isnan(r)).sum()))]))
    print(" pct 50/90/99:", np.nanpercentile(r, [50, 90, 99]))
    for j in o[:4]:
        p = pools[j]; x = rows[p]; ev = EV[p]
        liqs = sorted(set(s[6] for s in ev["sw"]))
        print("  ", p[:12], f"ret {r[j]:.2f}", "fee", x["fee"], "ts", x["tick_spacing"], "mods", [(m[0]-x["launch_block"], m[2], m[3], f"{m[4]:.3g}") for m in ev["mods"]][:6], "n distinct liq", len(liqs), "tick0", x["tick0"])
