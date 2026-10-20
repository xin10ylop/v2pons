"""Find the Ethereum-side fills of the two 2.433 hub deposits (origin chain 4663) and decode them; inspect the recipient 0x4216e5ae on chain 1."""
import sys, json; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
DEP = {"0x1e1518c5d839c3cf83789d2d8d057f24e5bde75573295c8a0e6f07ca51a7ea21": 0.1, "0xe766eb3cc7689edd5aef988da2273d2439bd44e74021458aac2602d068fa51b3": 9.199}
ORIG = "0x" + "%064x" % 4663
t0 = 1791810525  # 13:08:45 Oct 12
b0 = rpcx.block_at("eth_h", t0 - 120); b1 = rpcx.block_at("eth_h", t0 + 2 * 3600)
print("eth blocks", b0, b1)
hits = rpcx.logs("eth_h", {"topics": [None, ORIG]}, b0, b1, maxspan=50)
print("logs with topic1=4663:", len(hits))
for l in hits: print(" ", l["address"], int(l["blockNumber"], 16), l["transactionHash"], l["topics"][0][:12], l["topics"][2] if len(l["topics"]) > 2 else "")
json.dump(hits, open("c02_fill_logs.json", "w"), indent=1)
R = "0x4216e5ae6021c523aae05b6ac6824f3c096cf905"
c = rpcx.call("eth_h", "eth_getCode", [R, "latest"]); print("recipient code len on eth", (len(c) - 2) // 2, c[:120])
open("code_recipient_eth.hex", "w").write(c)
print(rpcx.STATS)
