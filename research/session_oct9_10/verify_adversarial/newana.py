import sys, json, collections, time; sys.path.insert(0, "..")
from chain import *
D = json.load(open("newsch.json")); P, ev, TX, head = D["P"], D["ev"], D["TX"], D["head"]
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(P, key=lambda p: P[p]["b0"])
bts = batch([("eth_getBlockByNumber", [hex(P[p]["b0"]), False]) for p in pids])
wallets = collections.Counter()
for p in pids:
    for l in ev[p]:
        if l["topics"][0] == T_SWAP: wallets[TX[l["transactionHash"]][0]] += 1
print("most active swap wallets:", [(w[:10], n) for w, n in wallets.most_common(8)])
for p, b in zip(pids, bts):
    q = P[p]; b0 = q["b0"]; ts = int(b["timestamp"], 16)
    ls = sorted(ev[p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    rows = []; pull = None
    for l in ls:
        bn = int(l["blockNumber"], 16) - b0; t = TX[l["transactionHash"]]
        if l["topics"][0] == T_SWAP:
            a0 = s128(W(l["data"], 0))
            rows.append((bn, "B" if a0 < 0 else "S", abs(a0) / 1e18, t[0][2:8], t[2]))
        else:
            dl = sgn(W(l["data"], 2))
            if dl < 0 and pull is None: pull = bn
    buys = [r for r in rows if r[1] == "B" and r[2] >= 2e-4]
    sells = [r for r in rows if r[1] == "S"]
    first = buys[0][0] if buys else None
    hi_nonce = [r for r in buys if r[4] > 2]
    print(f"{time.strftime('%H:%M:%S', time.gmtime(ts))} fee {q['fee']/1e4:g}% dep {q['dep'][2:8]} launcher {q['launcher'][2:8]} | real buys {len(buys)} first +{first} | blocks of first 6: {[r[0] for r in buys[:6]]} | pull +{pull} | buys by nonce>2 wallets: {[(r[0], round(r[2],4), r[3], r[4]) for r in hi_nonce[:4]]} | sells {len(sells)}")
