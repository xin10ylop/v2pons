"""V3 crowd line: per 24-h window, the first real buy offset (p50), the share of launches with a real buy by +60 / +80, the median wave
ETH in [frb, frb+20], and the earliest pull of launches without a real buy (does the crowd arrive later, does the operator pull earlier?)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s15_honest as H
L = [r for r in H.R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
for d in range(7):
    xs = [r for r in L if H.day(r) == d]; f = sorted(r["frb"]["off"] for r in xs if r["frb"])
    nof = sorted(r["first_pull_off"] for r in xs if not r["frb"] and r["first_pull_off"] is not None)
    wave = sorted(sum(dq for off, dq, e in H.buys(r) if r["frb"]["off"] <= off <= r["frb"]["off"] + 20 and dq >= 5e15) / 1e18 for r in xs if r["frb"])
    print(f"d{d}: n {len(xs)} real buy {len(f)} p50 off {f[len(f)//2]}  by+60 {sum(1 for x in f if x <= 60)/len(xs):.2f} by+80 {sum(1 for x in f if x <= 80)/len(xs):.2f}  wave ETH p50 {wave[len(wave)//2]:.3f}  no-crowd pools pulled at min/p50 {nof[0] if nof else None}/{nof[len(nof)//2] if nof else None} (n {len(nof)})")
