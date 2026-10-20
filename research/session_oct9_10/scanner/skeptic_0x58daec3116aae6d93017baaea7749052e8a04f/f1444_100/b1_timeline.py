import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
K1 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
K2 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"
pids = F[K1]['pids'] + F[K2]['pids']
E = load_events(pids)
json.dump({'pools': {p: P[p] for p in pids}, 'events': {p: E[p] for p in pids}}, open('fam_raw.json', 'w'))
for p in pids:
    r = P[p]; e = E[p]; lb = r['launch_block']
    lt = T.get(r['launch_tx'])
    print(f"\n=== {p[:10]} fee {r['fee']} lb {lb} ts {r['launch_ts']} val {r['launch_value_eth']} from {r['launch_from'][:10]} nonce {r['launch_nonce']} tick0 {r['tick0']} L {r['liq_launch']} nsw {len(e['swaps'])} pulls {len(e['pulls'])} adds {len(e['adds'])}")
    for s in e['swaps']:
        tx = T.get(s['tx'])
        ti = '' if not tx else f"{tx['from'][:10]} n{tx['nonce']} ->{(tx['to'] or 'create')[:10]} {tx['selector']} {tx['calldata_len']} v{tx['value_eth']}"
        print(f"  +{s['bn']-lb:5d} ti{s['ti']:3d} {'BUY ' if s['a0']<0 else 'SELL'} {abs(s['a0'])/1e18:.6f} snd {s['sender'][:10]} {ti}")
    for q in e['pulls']:
        tx = T.get(q['tx'])
        print(f"  +{q['bn']-lb:5d} PULL dl {q['dl']} {q['lo']}..{q['hi']} {'' if not tx else tx['from'][:10]+' '+tx['selector']}")
    for q in e['adds'][1:]:
        print(f"  +{q['bn']-lb:5d} ADD dl {q['dl']}")
