import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
US = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
wl = collections.defaultdict(set); maxbuy = collections.defaultdict(float)
for n, pid in enumerate(pids):
    P = D["pools"][pid]; b0 = P["meta"]["block"]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    for e in P["ev"]:
        if e["t0"] != T_SWAP: continue
        a0 = s128(W(e["data"], 0)); t = P["txs"].get(e["tx"])
        if t and a0 < 0: wl[t["from"]].add(n); maxbuy[t["from"]] = max(maxbuy[t["from"]], -a0/1e18)
print("small multi-launch buyers:", [(w[:10], len(v), round(maxbuy[w], 6)) for w, v in wl.items() if len(v) >= 3 and maxbuy[w] < 2e-4])
for n, pid in enumerate(pids):
    P = D["pools"][pid]; m = P["meta"]; b0 = m["block"]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    for e in P["ev"]:
        if e["t0"] != T_SWAP: continue
        a0 = s128(W(e["data"], 0)); t = P["txs"].get(e["tx"])
        if not t or a0 > -2e14 or e["bn"] >= pull: continue
        w = t["from"]
        if w in (US, DUST) or len(wl[w]) >= 3 or t["nonce"] <= 1: continue
        print(f"{n:3d} {m['kind']} +{e['bn']-b0:5d} (pull +{pull-b0 if pull<10**12 else None}) {w[:10]} nonce {t['nonce']} {-a0/1e18:.5f} ETH launches {sorted(wl[w])} to {t['to'][:10]} via {e['sender'][:8]}")
