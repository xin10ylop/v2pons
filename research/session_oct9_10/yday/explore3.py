import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
wl = collections.defaultdict(list)   # wallet -> [(launch#, offset, eth, nonce)]
rows = []
for n, pid in enumerate(pids):
    P = D["pools"][pid]; m = P["meta"]; b0 = m["block"]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    buys = []
    for e in P["ev"]:
        if e["t0"] != T_SWAP: continue
        a0 = s128(W(e["data"], 0)); t = P["txs"].get(e["tx"])
        if t and a0 < 0 and e["bn"] < pull:
            wl[t["from"]].append((n, e["bn"] - b0, -a0 / 1e18, t["nonce"])); buys.append((e["bn"] - b0, t["from"], -a0/1e18, t["nonce"]))
    rows.append((n, pid, m, pull - b0 if pull < 10**12 else None, buys))
# wallets on 2..20 launches with any real buy
print("wallets with real-size buys on 2-25 launches:")
for w, v in sorted(wl.items(), key=lambda kv: -len({x[0] for x in kv[1]})):
    L = sorted({x[0] for x in v})
    if 2 <= len(L) <= 25 and max(x[2] for x in v) >= 2e-4:
        print(f"  {w[:10]} launches {len(L)} {L[:14]} offsets {[x[1] for x in v][:8]} eth {[round(x[2],4) for x in v][:5]} nonces {[x[3] for x in v][:5]}")
print()
for n, pid, m, pull, buys in rows:
    real = [b for b in buys if b[2] >= 2e-4]
    fresh = sum(1 for b in real if b[3] == 0)
    print(f"{n:3d} {time.strftime('%H:%M', time.gmtime(m['ts']))} {m['kind']} fee {m['fee']:5d} pull {pull} first real {real[0][0] if real else None} nreal {len(real)} fresh {fresh} wallets {len({b[1] for b in real})}")
