import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
FAMS = json.load(open("families_in.json"))
P = load_pools(); F = load_families(); T = load_txs()
pids = [pid for k in FAMS for pid in F[k]["pids"]]
E = load_events(set(pids))
for k in FAMS:
    print("=" * 30, k)
    for pid in F[k]["pids"]:
        p = P[pid]; e = E.get(pid)
        print(f"-- {pid[:12]} b0 {p['launch_block']} ts {p['launch_ts']} from {p['launch_from'][:10]} nonce {p['launch_nonce']} val {p['launch_value_eth']} tick0 {p['tick0']} liq {p['liq_launch']} nsw {p['n_swaps']} buys {p['n_buys']} sells {p['n_sells']} pulls {p['n_pulls']} adds {p['n_adds']} ethin {p['eth_in_buys']:.5f}")
        if not e: continue
        for a in e["adds"][:3]:
            print(f"   add +{a['bn']-p['launch_block']} lo {a['lo']} hi {a['hi']} dl {a['dl']} tx {a['tx'][:10]}")
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print(f"   sw +{s['bn']-p['launch_block']:5d} ti {s['ti']:3d} {'BUY ' if s['a0']<0 else 'SELL'} {abs(s['a0'])/1e18:.6f} fee {s['fee']} snd {s['sender'][:10]} " + (f"to {(t['to'] or '')[:10]} from {t['from'][:10]} sel {t['selector']} len {t['calldata_len']} nonce {t['nonce']}" if t else ""))
        for s in e["pulls"][:2]:
            t = T.get(s["tx"])
            print(f"   PULL +{s['bn']-p['launch_block']} dl {s['dl']} snd {s['sender'][:10]} " + (f"to {(t['to'] or '')[:10]} from {t['from'][:10]} sel {t['selector']}" if t else ""))
