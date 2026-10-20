"""Ethereum: the 20 bot-buyer wallets' transactions from the 2.433 pool's launch block to now (where their ETH went)."""
import sys, json, time, collections; sys.path.insert(0, '.'); import rpcx, walletx
D = json.load(open("c09_eth_pool.json"))
W = sorted(set(r["from"] for r in D["rows"] if r["k"] == "swap" and r["sel"] in ("0xc1120e3d", "0x24856bc3")))
h, _ = rpcx.head("eth_h"); res = {}; dest = collections.Counter(); amt = collections.Counter()
for w in W:
    n0, n1, T = walletx.txs("eth_h", w, 26176827, h)
    res[w] = T
    for t in T:
        print(w[:10], time.strftime("%m-%d %H:%M:%S", time.gmtime(t["ts"])), t["b"], "n", t["nonce"], "to", t["to"], "v %.6f" % t["v"], t["sel"], t["len"], flush=True)
        if t["sel"] == "0x": dest[t["to"]] += 1; amt[t["to"]] += t["v"]
print("plain ETH destinations:", [(k, dest[k], round(amt[k], 6)) for k in dest])
json.dump(res, open("c15_eth_buyers_after.json", "w"), indent=1)
