"""Every pool of the non-dust early buyers (0x5b0320fb, 0x5373fb35, 0xc2101da8, 0xbd9dc5f6, 0x2eb9009a) and of our relay: buy offset from T,
size, own sell, pull - T, the router's buys after T+62 before the pull. (offline, c05)"""
from common import *
D = json.load(open(J("c05_pools.json"))); P = D["pools"]
WL = {"0x5b0320fb": "0x5b0320fb", "0x5373fb35": "0x5373fb35", "0xc2101da8": "0xc2101da8", "0xbd9dc5f6": "0xbd9dc5f6", "0x2eb9009a": "0x2eb9009a", "ours": WALLET[:10]}
for nm, pre in WL.items():
    print(f"\n== {nm}")
    for p in sorted(P, key=lambda p: p["lb"]):
        bs = [s for s in p["sw"] if s["buy"] and s.get("from", "")[:10] == pre]
        if not bs: continue
        s = bs[0]; sl = [x for x in p["sw"] if not x["buy"] and x.get("from", "")[:10] == pre and (x["bn"], x["li"]) > (s["bn"], s["li"])]
        T = p["T"]
        nra = None if T is None else sum(1 for x in p["sw"] if x["buy"] and x["cls"] == "router" and x["off"] > T + 62 and (p["pull"] is None or x["off"] < p["pull"]))
        print(f"  {utc(p['ts'])} {p['pid'][:12]} T {T} buy {'T%+d' % (s['off'] - T) if T is not None else '+%d' % s['off']} {s['eth']:.5f} sold {'+%d' % (sl[0]['off'] - s['off']) if sl else '-'}"
              f" | pull {'T+%d' % (p['pull'] - T) if (p['pull'] is not None and T is not None) else p['pull']} (buy+{None if p['pull'] is None else p['pull'] - s['off']}) | router buys after T+62: {nra} | age {p['age']}")
