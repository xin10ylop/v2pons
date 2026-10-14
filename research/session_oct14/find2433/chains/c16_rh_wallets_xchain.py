"""The Robinhood 2.433 wallets (31 bot buyers, 150 launch wallets) on Ethereum, Base, Arbitrum, Unichain and BNB: nonce and balance now."""
import sys, json, collections; sys.path.insert(0, '.'); import rpcx
b = json.load(open("/home/user/v2pons/research/session_oct12/v2433/wallets/w05_buyers_now.json"))
l = json.load(open("/home/user/v2pons/research/session_oct12/v2433/wallets/w15_launchw_now.json"))
def addrs(x):
    if isinstance(x, dict): return list(x.keys()) if all(k.startswith("0x") for k in x) else [v.get("w") or v.get("a") for v in x.values()]
    return [y if isinstance(y, str) else (y.get("w") or y.get("a") or y.get("addr")) for y in x]
B = addrs(b["ws"]); L = addrs(l["w"])
print(len(B), "buyers", B[:2], len(L), "launch wallets", L[:2])
out = {}
for name, S in [("buyers", B), ("launch", L)]:
    for ch in ["eth", "base", "arb", "uni", "bsc"]:
        n = rpcx.batch(ch, "eth_getTransactionCount", [[a, "latest"] for a in S], n=20)
        bal = rpcx.batch(ch, "eth_getBalance", [[a, "latest"] for a in S], n=20)
        n = [int(x, 16) if x else -1 for x in n]; bal = [int(x, 16) / 1e18 if x else 0 for x in bal]
        out[f"{name}_{ch}"] = list(zip(S, n, bal))
        nz = [(a[:10], k, round(v, 5)) for a, k, v in zip(S, n, bal) if k > 0 or v > 0]
        print(name, ch, "with nonce>0 or balance>0:", len(nz), "of", len(S), "| nonce p50/max", sorted(n)[len(n) // 2], max(n), "| sum bal %.4f" % sum(bal), nz[:6])
json.dump(out, open("c16_rh_wallets_xchain.json", "w"))
