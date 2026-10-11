"""Per family, from pools rows only: crosstabs, launches by day, launch shape, liq_off, first real buy, pulls, reaction."""
import sys, os, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); FP4 = fam_pools(R, v23_only=False)
def q(xs, ps=(.1, .5, .9)):
    xs = sorted(x for x in xs if x is not None)
    return "/".join(str(round(xs[min(len(xs)-1, int(p*len(xs)))], 4)) for p in ps) if xs else "-"
DAYS = ["10-04", "10-05", "10-06", "10-07", "10-08", "10-09", "10-10", "10-11"]
for name, rs in FP.items():
    allr = FP4[name]
    print(f"\n######## {name}: V2/V3 n={len(rs)} (with v4: {len(allr)})  dex {Counter(r['dex'] for r in allr).most_common()}")
    if not rs: continue
    print("  tok:", Counter(r['fam']['tok'][:8] for r in rs).most_common(4), " lc:", Counter((r['fam']['lc'] or '')[:8]+'|'+(r['fam']['lc'] or '').split('|')[-1] for r in rs).most_common(4))
    print("  by day:", [(d, sum(1 for r in rs if r['launch_utc'][5:10] == d)) for d in DAYS])
    L = [r['launch'] for r in rs]
    print("  launch to:", Counter(l['to'] for l in L).most_common(3), " sel/clen:", Counter((l['selector'], l['calldata_len']) for l in L).most_common(4))
    print("  value:", Counter(round(l['value_eth'], 4) for l in L).most_common(6), " fee/ts:", Counter((r['fee'], r['tick_spacing']) for r in rs).most_common(3), " n_pools_in_tx:", Counter(l['n_pools_in_tx'] for l in L).most_common(3))
    print("  launch wallets:", len(set(l['from'] for l in L)), " nonce:", q([l['nonce'] for l in L]), " created_contract:", sum(1 for l in L if l['created_contract']), " token_code size:", Counter(r['token_code']['size'] for r in rs).most_common(3))
    print("  liq: with adds", sum(1 for r in rs if r['n_adds']), " liq_in_launch_tx", sum(1 for r in rs if r['liq_in_launch_tx']), " liq_off p10/50/90", q([r['liq_off'] for r in rs]))
    frb = [r for r in rs if r['frb']]
    print(f"  frb: {len(frb)}/{len(rs)}  off {q([r['frb']['off'] for r in frb])}  eth {q([r['frb']['eth'] for r in frb])}  idx {q([r['frb']['idx'] for r in frb])}")
    if frb:
        print("   frb to/sel/clen:", Counter((r['frb']['to'], r['frb']['sel'], r['frb']['clen']) for r in frb).most_common(3), " router:", Counter(r['frb']['router'] for r in frb).most_common(2))
        print("   frb eoa distinct", len(set(r['frb']['eoa'] for r in frb)), " is launch wallet", sum(1 for r in frb if r['frb']['eoa_is_launch_wallet']), " eoa npools_seen", q([r['frb']['eoa_npools_seen'] for r in frb]), " also_in_tok_family>0", sum(1 for r in frb if (r['frb']['also_in_tok_family'] or 0) > 0), " prio", Counter(r['frb']['prio'] for r in frb).most_common(3))
        print("   frb_off - liq_off:", q([r['frb']['off'] - (r['liq_off'] or 0) for r in frb]))
    pl = [r for r in rs if r['n_pulls']]
    print(f"  pulled {len(pl)}/{len(rs)}  first pull off {q([r['first_pull_off'] for r in pl])}  full {sum(1 for r in pl if r['first_pull_full'])}  by launch wallet {sum(1 for r in pl if r['pull_by_launch_wallet'])}  before frb {sum(1 for r in pl if r['pull_before_frb'])}  pull-frb {q([r['pull_minus_frb'] for r in pl])}")
    if pl: print("   pull via:", Counter((p[2], p[3]) for r in pl for p in r['pulls'][:1]).most_common(3))
    o12 = [r for r in rs if r['ev_complete'] and r['outsider12'].get('n', 0) > 0]
    o12nf = [r for r in rs if r['ev_complete'] and r['outsider12'].get('nf_n', 0) > 0]
    base = [r for r in rs if r['ev_complete'] and r['outsider12'].get('n', 0) == 0 and r['outsider12'].get('n_buys12_before_pull', 0) > 0]
    print(f"  outsider12 reaction {sum(1 for r in o12 if r['outsider12'].get('reaction'))}/{len(o12)}  nf {sum(1 for r in o12nf if r['outsider12'].get('nf_reaction'))}/{len(o12nf)}  baseline {sum(1 for r in base if (r['pull_after_last_buy12'] is not None and r['pull_after_last_buy12'] <= 30))}/{len(base)}")
    print("  n_swaps", q([r['n_swaps'] for r in rs]), " n_buys", q([r['n_buys'] for r in rs]), " n_sells", q([r['n_sells'] for r in rs]), " buy_eth_total", q([r['buy_eth_total'] for r in rs]))
