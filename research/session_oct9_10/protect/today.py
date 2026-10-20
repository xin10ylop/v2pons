import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load import *
pools = load()
for p in pools:
    ours = [x for x in p["sw"] if is_us(x)]
    if not ours or p["b0"] < 83719339: continue
    B = ours[0]["bn"]; b0 = p["b0"]
    print(f"\n=== {p['pid'][:10]} {utc(p['ts'])} fee {p['fee']} deployer {p['deployer'][:10]} pull {p['pull']['bn']-b0 if p['pull'] else None} (buy+{p['pull']['bn']-B if p['pull'] else None}) pull from {p['pull']['from'] if p['pull'] else None} nonce {p['pull']['nonce'] if p['pull'] else None}")
    for x in p["sw"]:
        if x["bn"] > (p["pull"]["bn"] + 3 if p["pull"] else B + 30): break
        if x["bn"] < B - 60 and x["a0"] > -REAL: continue
        f = x["fp"] or {}
        print(f"  +{x['bn']-b0:5d} (B{x['bn']-B:+4d}) idx {x['idx']} {'US ' if is_us(x) else '   '}{'BUY ' if x['a0']<0 else 'sell'} {abs(x['a0'])/1e18:.6f} from {x['from']} n {x['nonce']} via {x['via'][:8]} to {x['to'][:10] if x['to'] else None} sel {x['sel']} fp t{f.get('type')} gas {f.get('gas')} prio {f.get('prio')} len {f.get('len')} dlmax {f.get('dl_max')}")
    for m in p["mls"][:4]:
        print(f"  ML +{m['bn']-b0} (B{m['bn']-B:+d}) dl {m['dl']:.3e} from {m['from']} n {m['nonce']} to {m['to']} sel {m['sel']} idx {m['idx']}")
