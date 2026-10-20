import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
KEYS = json.load(open("keys.json"))
pids = set(p for k in KEYS for p in F[k]["pids"])
E = load_events(pids)
for k in KEYS:
    print("=" * 30, k)
    for pid in F[k]["pids"]:
        p = P[pid]; e = E.get(pid) or {}
        print(f"-- {pid[:12]} b0 {p['launch_block']} ts {p['launch_ts']} from {p['launch_from'][:10]} nonce {p['launch_nonce']} val {p['launch_value_eth']} tick0 {p['tick0']} liq {p['liq_launch']} token {p['token'][:10]} hooks {p['hooks'][:10]} nsw {p['n_swaps']} nb {p['n_buys']} ns {p['n_sells']} npull {p['n_pulls']} nadd {p['n_adds']} ethin {p['eth_in_buys']}")
        for a in e.get("adds", [])[:3]:
            print(f"   add +{a['bn']-p['launch_block']} lo {a['lo']} hi {a['hi']} dl {a['dl']} tx {a['tx'][:10]} {'LAUNCH' if a['tx']==p['launch_tx'] else ''}")
        for s in e.get("swaps", [])[:14]:
            t = T.get(s["tx"]); 
            print(f"   sw +{s['bn']-p['launch_block']} ti {s['ti']} {'BUY ' if s['a0']<0 else 'SELL'} {abs(s['a0'])/1e18:.6f} fee {s['fee']} sender {s['sender'][:10]} to {(t['to'] or '')[:10] if t else '?'} from {t['from'][:10] if t else '?'} sel {t['selector'] if t else '?'} len {t['calldata_len'] if t else '?'} {'LAUNCHTX' if s['tx']==p['launch_tx'] else ''}")
        for pl in e.get("pulls", [])[:2]:
            print(f"   pull +{pl['bn']-p['launch_block']} dl {pl['dl']} sender {pl['sender'][:10]}")
