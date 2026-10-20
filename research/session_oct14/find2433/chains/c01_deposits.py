"""Re-read the two 2.433 hub bridge deposits on Robinhood Chain: full FundsDeposited data incl. message; the deposit txs; reference code hashes."""
import sys, json; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
TX = ["0x0bad72bd9db03b99a0563d8daac9914ee7d04a9df82c2fb9ef54c9e64d5541b3", "0x9b57f4e6d10fa22ca39d066d5bf1113f94dfc938411459b3a34eefb6ac5247f3",
      "0x8d18b0ee04940255815ec638c86e90570bb8dfd6fb3a360e677a62fa86b8ddcf", "0xc04476ce4a9676852106a1e35ad37b2be0aaa9425a28af70a5d45cebb922f5d3"]
out = {}
for h in TX:
    t = rpcx.call("rh", "eth_getTransactionByHash", [h]); r = rpcx.call("rh", "eth_getTransactionReceipt", [h])
    print("TX", h, "from", t["from"], "to", t["to"], "value", int(t["value"], 16) / 1e18, "block", int(t["blockNumber"], 16), "inputlen", (len(t["input"]) - 2) // 2)
    print("  input", t["input"][:2000])
    for l in r["logs"]:
        print("  LOG", l["address"], l["topics"], "data", l["data"][:3000])
    out[h] = {"tx": t, "logs": r["logs"]}
json.dump(out, open("c01_deposit_txs.json", "w"), indent=1)
ref = {}
for name, a in [("token2433", "0xb28f2d1f01b659bdffd762f4fac660dd25057777"), ("botrouter", "0x1cbaf24d53fe930fce8eff149fa797d2611da149"),
                ("spoke_rh", "0xd29c85f15df544ba632c9e25829fd29d767d7978"), ("dep_contract", "0x794dbdbdbfd3f8a3b887f4513bf5ff29edd04a94"), ("relay_998d", "0x998d7c17")]:
    if len(a) != 42: continue
    c = rpcx.call("rh", "eth_getCode", [a, "latest"])
    ref[name] = {"addr": a, "len": (len(c) - 2) // 2, "hash": "0x" + keccak(hexstr=c).hex() if len(c) > 2 else None}
    open(f"code_{name}.hex", "w").write(c)
    print(name, ref[name])
json.dump(ref, open("c01_refcode.json", "w"), indent=1)
print(rpcx.STATS)
