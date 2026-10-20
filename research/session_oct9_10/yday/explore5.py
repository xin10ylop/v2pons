import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
wl = collections.defaultdict(set)
for n, pid in enumerate(pids):
    P = D["pools"][pid]
    for e in P["ev"]:
        t = P["txs"].get(e["tx"])
        if t and e["t0"] == T_SWAP and s128(W(e["data"], 0)) < 0: wl[t["from"]].add(n)
for n in [int(x) for x in sys.argv[1:]]:
    pid = pids[n]; P = D["pools"][pid]; m = P["meta"]; b0 = m["block"]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    print(f"\n== {n} {pid[:10]} {m['kind']} fee {m['fee']} pull +{pull-b0}")
    for e in P["ev"]:
        if e["bn"] < pull - 40 or e["bn"] > pull + 2: continue
        t = P["txs"].get(e["tx"], {})
        if e["t0"] == T_SWAP:
            a0 = s128(W(e["data"], 0)); print(f"   +{e['bn']-b0:5d} idx {t.get('idx')} {'buy ' if a0<0 else 'sell'} {abs(a0)/1e18:.6f} from {t.get('from','')[:10]} nonce {t.get('nonce')} via {e['sender'][:8]} launches {len(wl[t.get('from')])}")
        else:
            print(f"   +{e['bn']-b0:5d} idx {t.get('idx')} ML {sgn(W(e['data'],2)):.3e} from {t.get('from','')[:10]}")
