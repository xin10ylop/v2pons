import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
keys = json.load(open(sys.argv[1]))
pids = set()
for k in keys: pids |= set(F[k]["pids"])
E = load_events(pids)
for k in keys:
    f = F[k]
    print("=" * 100); print(k)
    print({x: f.get(x) for x in ("count", "values_eth", "n_deployers", "top_deployers", "nonce_med", "first_block", "last_block", "to_code_size", "swap_tx_to_top", "first_pull_to_sel_top", "first_buy_rel_p10_50_90", "first_pull_rel_p10_50_90", "first_buy_eth_p10_50_90", "n_no_pull_in_window", "hooks")})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid) or {}
        print(f"-- {pid[:12]} b0 {p['launch_block']} ts {p['launch_ts']} from {p['launch_from'][:10]} nonce {p['launch_nonce']} val {p['launch_value_eth']} tick0 {p['tick0']} liq {p['liq_launch']} token {p['token'][:10]} nsw {p['n_swaps']} nb {p['n_buys']} ns {p['n_sells']} npull {p['n_pulls']} nadd {p['n_adds']} fb {p['first_buy_rel']} {p['first_buy_eth']} fp {p['first_pull_rel']} pullfrom {p['first_pull_from']} pullto {p['first_pull_to']} {p['first_pull_selector']}")
        for a in (e.get("adds") or [])[:4]:
            print(f"    add bn+{a['bn']-p['launch_block']} lo {a['lo']} hi {a['hi']} dl {a['dl']} tx {a['tx'][:10]} {'LAUNCH' if a['tx']==p['launch_tx'] else ''}")
        for s in (e.get("swaps") or [])[:12]:
            t = T.get(s["tx"])
            print(f"    sw +{s['bn']-p['launch_block']} ti {s['ti']} a0 {s['a0']/1e18:+.6f} fee {s['fee']} sender {s['sender'][:10]} " + (f"to {t['to'][:10] if t['to'] else None} from {t['from'][:10]} sel {t['selector']} clen {t['calldata_len']} nonce {t['nonce']} val {t['value_eth']}" if t else "notx"))
        for pu in (e.get("pulls") or [])[:3]:
            print(f"    pull +{pu['bn']-p['launch_block']} dl {pu['dl']} sender {pu['sender'][:10]}")
