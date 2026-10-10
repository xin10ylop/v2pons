import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pricer6 import *
P = load_pools(); rows = json.load(open(os.path.join(HERE, "calib_live_minout.json")))
hi = sorted([r for r in rows if r["defense"] and r["bot"]], key=lambda r: -r["eth_ahead_incl_relay"])[:3]
pids = [r["pid"] for r in hi]
res = [json.loads(l) for l in open(os.path.join(HERE, "pools.jsonl"))]
drop = [r["pid"] for r in res if r["fam"] == "control:vbot-v2.433" and r["front"] and r["front"].get("dropped")][:3]
E = load_events(set(pids + drop)); T = load_txs(); M = load_blocks_meta()
for pid in pids + drop:
    pl = Pool(P[pid], E[pid], T, M)
    print("==", pid[:12], "relay pool" if pid in pids else "DROPPED in model", "L0", pl.L0, "fee", pl.fee)
    for x in pl.seq[:10]:
        print(f"   +{x['rel']:3d} li {x['li']:3d} {'BUY ' if x['buy'] else 'SELL'} {x['eth']/1e18:.6f} from {str(x['from'])[:10]} to {str(x['to'])[:10]} sel {x['sel']} relay {x['relay']} sp {x['sqrt_p']} liq {x['liq']}" + (f" mo/out {vbot_minout(x)/x['a1']:.5f}" if vbot_minout(x) else ""))
