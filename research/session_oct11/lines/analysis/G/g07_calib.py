"""calibration: the vbot 2.433 shape family under the grid (K = 1..3, sell into the next buy >= X, take-profit, fixed holds), per day"""
from gstats import *
Q = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0058
rows = {r["pool"]: r for r in load_rows()}
kept = json.load(open(os.path.join(G, "families_kept.json")))
fk = [k for k in kept if k.startswith("shape=") and k.endswith("|2.4333285")][0]
pools = kept[fk]
grid = load_grid(Q)
ts = np.array([rows[p]["launch_ts"] for p in pools]); dy = np.array([day(t) for t in ts])
for cons in (False, True):
    ret, pulled, so = fam_returns(grid, pools, conservative=cons)
    print(f"\n=== {fk}  n {len(pools)}  q {Q}  pull rule: {'pull at or before the sell block' if cons else 'pull before the sell block (brief)'}")
    print("rule".ljust(24), "n".rjust(5), "mean".rjust(7), "med".rjust(7), "win".rjust(5), "pulled".rjust(7), " per day (d1..d7, d7 = last 24 h)")
    for K in (1, 2, 3):
        ki = gsim.KS.index(K)
        for i, (t, p, H) in enumerate(gsim.RULES):
            if not ((t == "X" and H in (10, 15, 20, 30)) or (t == "TP" and p in (0.01, 0.02, 0.03, 0.05) and H in (10, 15, 20)) or (t == "H" and H in (10, 15, 20))): continue
            r = ret[:, ki, i]; m = ~np.isnan(r)
            pdays = " ".join(f"{np.nanmean(r[dy == d])*100:+5.1f}" for d in range(7))
            print(gsim.rule_name(K, i).ljust(24), f"{m.sum():5d} {np.nanmean(r)*100:+6.1f}% {np.nanmedian(r)*100:+6.1f}% {np.nanmean(r[m] > 0):5.0%} {pulled[:, ki, i][m].mean():6.1%}  {pdays}")
# the operator's first real buy and the pull, per day
print("\nper day: launches, frb present, frb offset median, frb by router 0x1cbaf24d, pulled within 30 blocks, first pull offset median, pull before frb")
for d in range(7):
    rs = [rows[p] for p, dd in zip(pools, dy) if dd == d]
    frb = [r["frb"] for r in rs if r.get("frb")]
    po = [r["first_pull_off"] for r in rs if r["first_pull_off"] is not None]
    print(d + 1, len(rs), len(frb), np.median([f["off"] for f in frb]) if frb else None, sum(1 for f in frb if (f.get("to") or "").startswith("0x1cbaf24d")),
          sum(1 for x in po if x <= 30), np.median(po) if po else None, sum(1 for r in rs if r.get("pull_before_frb")))
