import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json")); FP = json.load(open("react_fp.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
byw = collections.defaultdict(collections.Counter); wl = collections.defaultdict(set); wmax = collections.defaultdict(float)
for n, pid in enumerate(pids):
    P = D["pools"][pid]
    for e in P["ev"]:
        if e["t0"] != T_SWAP or e["tx"] not in FP: continue
        a0 = s128(W(e["data"], 0)); t = P["txs"][e["tx"]]; f = FP[e["tx"]]
        if a0 >= 0: continue
        key = (f["type"], f["gas"], f["prio"], f["len"], f["dl_max"], e["sender"][:8])
        byw[t["from"]][key] += 1; wl[t["from"]].add(n); wmax[t["from"]] = max(wmax[t["from"]], -a0 / 1e18)
allfp = collections.Counter()
for w, c in byw.items():
    for k, v in c.items(): allfp[k] += v
print("fingerprints (type, gas, prio, len, deadline=max, via):")
for k, v in allfp.most_common(40):
    ws = [w for w in byw if k in byw[w]]
    print(f"  {k}: {v} buys, {len(ws)} wallets, e.g. {[w[:10] for w in ws[:6]]}")
crowd_fp = lambda k: k[1] == 220000 and k[2] == 20000000 and k[4] is True
mixed = [w for w in byw if any(crowd_fp(k) for k in byw[w]) and not all(crowd_fp(k) for k in byw[w])]
print("wallets with mixed fingerprints:", [(w[:10], dict(byw[w])) for w in mixed[:10]])
