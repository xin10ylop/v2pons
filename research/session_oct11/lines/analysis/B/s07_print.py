"""Readable dump of fam_results.json (fam_results.txt): shape, first real buy, wave, pulls, and every replay rule with $/day."""
import sys
from common import *
R = json.load(open(os.path.join(D, sys.argv[1] if len(sys.argv) > 1 else "fam_results.json")))
def f(x, p=False):
    if x is None: return "-"
    return f"{x:.0%}" if p else (f"{x:.3g}" if isinstance(x, float) else str(x))
lines = []
for k, v in R.items():
    s, b, w, pl = v["shape"], v["frb"], v["wave"], v["pulls"]
    lines.append(f"\n##### {short(k)}  n={v['n']} ({v['n']/7:.1f}/d; by day {s['perday']}) wallets {s['wallets']}")
    lines.append(f"  launch to {s['to']} | hash {s['target_hash']} | sel {s['selector']} | clen {s['clen']} | value {s['value']} | pools/tx {s['n_pools_in_tx']}")
    lines.append(f"  quote {s['quote']} | fee/ts {s['fee_ts']} | hooks {s['hooks']} | sqrt0 const {f(s['sqrt0_top'],1)} | mint liq const {f(s['liq_top'],1)} | liq_off {s['liq_off']}")
    lines.append(f"  FRB in {f(b['share'],1)} | off {b['off']} | eth {b['eth_p']} (size top {f(b['size_top'],1)}) | in launch tx {f(b['in_launch_tx'],1)} | launch wallet {f(b['lw'],1)} | eoas {b['eoas']} top {b['eoa_top']} | npools {b['npools_med']} | alsoLc {f(b['also_lc'],1)} | fp {b['fp']} | price move % {b['move']} | launch-tx move % {b['launch_tx_move']}")
    lines.append("  WAVE " + " | ".join(f"+{W}: n med {f(x['n_med'])} mean {f(x['n_mean'])} eth med {f(x['eth_med'])} mean {f(x['eth_mean'])} realbuy {f(x['real_any'],1)}" for W, x in w.items()))
    lines.append(f"  PULLS {f(pl['share'],1)} off {pl['off']} frac {f(pl['frac_med'])} full {f(pl['full'],1)} before frb {f(pl['before_frb'],1)} pull-frb {pl['pull_minus_frb']} by launch wallet {f(pl['by_lw'],1)} via {pl['via']} | react12nf {pl['react12nf']} base12 {pl['base12']}")
    for q, rr in v["replay"].items():
        stake = float(q) * 2570
        lines.append(f"  REPLAY q={q} (fixfront a={v['fixfront_a']}) skips {rr['skips']}")
        for nm, x in rr["rules"].items():
            if not x: continue
            dpd = x["mean"] * stake * x["n"] / 7
            bd = " ".join(f"{DAYS[int(d)]}:{c[0]}/{c[1]:+.2f}/{c[2]:.0%}" for d, c in sorted(x["byday"].items(), key=lambda kv: int(kv[0])))
            lines.append(f"    {nm:18s} n {x['n']:4d} mean {x['mean']:+.3f} med {x['med']:+.3f} win {x['win']:.0%} worst {x['worst']:+.2f} pulled {x['pulled']:.0%} $/d {dpd:+.1f} | {bd}")
open(os.path.join(D, "fam_results.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
