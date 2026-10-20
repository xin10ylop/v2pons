"""Router copies: nonce history (each token deploy through 7422a284 is one CREATE, +1 nonce) on Base and Ethereum, and creation time of the Base copy."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx, walletx
out = {}
hb, _ = rpcx.head("base_h"); he, _ = rpcx.head("eth_h")
for ch, ep, r, h, bt in [("base", "base_h", "0x814643195a74e6662dcccd681d70cfb36af4ee21", hb, 2.0), ("eth", "eth_h", "0xfac75d23e417ee39c180bbced4c665c9b57b83b2", he, 12.0)]:
    out[ch] = [(d, walletx.nonce(ep, r, h - int(d * 86400 / bt))) for d in [0, 1, 1.8, 2, 3, 7, 14, 30, 40, 60]]
    print(ch, r, "nonce (days ago, nonce):", out[ch], flush=True)
r = "0x814643195a74e6662dcccd681d70cfb36af4ee21"; lo, hi = hb - int(90 * 86400 / 2), hb
while hi - lo > 1:
    m = (lo + hi) // 2
    if len(rpcx.call("base_h", "eth_getCode", [r, hex(m)])) > 2: hi = m
    else: lo = m
out["base_created"] = [hi, rpcx.ts_of("base_h", hi)]
print("base router copy created at block", hi, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(out["base_created"][1])))
json.dump(out, open("c13_router_hist.json", "w"))
