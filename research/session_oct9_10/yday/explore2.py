import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
per = {"orig": collections.defaultdict(set), "copy": collections.defaultdict(set)}
for pid, P in D["pools"].items():
    m = P["meta"]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    for e in P["ev"]:
        if e["t0"] != T_SWAP: continue
        a0 = s128(W(e["data"], 0)); t = P["txs"].get(e["tx"])
        if t and a0 < 0 and e["bn"] < pull: per[m["kind"]][t["from"]].add(pid)
for k in per:
    print(k, sorted(((len(v), a[:10]) for a, v in per[k].items()), reverse=True)[:45])
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
def show(pid, n=40):
    P = D["pools"][pid]; m = P["meta"]; b0 = m["block"]
    print(f"\n== {pid[:10]} {m['kind']} block {b0} fee {m['fee']} deployer {m['from'][:10]} to {m['to'][:10]}")
    k = 0
    for e in P["ev"]:
        t = P["txs"].get(e["tx"], {})
        if e["t0"] == T_SWAP:
            a0 = s128(W(e["data"], 0)); print(f"   +{e['bn']-b0:5d} idx {t.get('idx')} {'buy ' if a0<0 else 'sell'} {abs(a0)/1e18:.6f} from {t.get('from','')[:10]} nonce {t.get('nonce')} via {e['sender'][:8]}")
        else:
            print(f"   +{e['bn']-b0:5d} ML {sgn(W(e['data'],2)):.3e} from {t.get('from','')[:10]}")
        k += 1
        if k >= n: break
for i in (0, 4, 33, 35, 41, 45, 70, 94, 97, 100): show(pids[i])
