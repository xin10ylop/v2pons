"""Monad sanity: topic0 tally from nad.fun bonding curve and CurveCreate from any emitter, over 30 x 100-block windows (last ~15 min)."""
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_hash.auto import keccak
url = "https://rpc.monad.xyz"; CURVE = "0xA7283d07812a02AFB7C09B60f8896bCEA3F90aCE"
CC = "0x" + keccak(b"CurveCreate(address,address,address,string,string,string,uint256,uint256,uint256)").hex()
CB = "0x" + keccak(b"CurveBuy(address,address,uint256,uint256)").hex()
h = rpc.block_number(url) - 3
ct = collections.Counter(); cc_emit = collections.Counter(); sw = collections.Counter()
SWAPS = ["0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f", "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67", "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"]
for i in range(30):
    a, b = h - (i + 1) * 100 + 1, h - i * 100
    for l in rpc.call(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": CURVE}]): ct[l["topics"][0]] += 1
    for l in rpc.call(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "topics": [[CC, CB]]}]): cc_emit[(l["address"], l["topics"][0][:10])] += 1
    for l in rpc.call(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "topics": [SWAPS]}]): sw[l["address"]] += 1
res = {"blocks": 3000, "curve_topic0s": ct.most_common(8), "CurveCreate_or_Buy_any_emitter": [[k[0], k[1], n] for k, n in cc_emit.most_common(5)],
       "CC": CC[:10], "CB": CB[:10], "swap_logs": sum(sw.values()), "top_swap_emitters": sw.most_common(5)}
print(json.dumps(res, indent=1)); json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "out", "monad_check.json"), "w"), indent=1)
