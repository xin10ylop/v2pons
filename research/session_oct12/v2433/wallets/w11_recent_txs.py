"""A wallet's most recent transactions inside the node's state window (about 5,000 blocks): binary search on the nonce, then the block's tx;
for swaps, the pool (from the receipt's Swap log) and its family."""
import os; os.environ["BLK_CACHE"] = "w11_blk_cache.jsonl"
from common import *
w = sys.argv[1].lower(); k = int(sys.argv[2]) if len(sys.argv) > 2 else 4
h, th = head(); lo0 = h - 4800
nonce = lambda b: int(rpc.call("eth_getTransactionCount", [w, hex(b)]), 16)
n_now, n_lo = nonce(h), nonce(lo0)
print(w, "nonce now", n_now, "4800 blocks ago", n_lo, f"({utc(th)})")
ini = {r["pid"]: r for r in jl(J("w01_inits_cache.jsonl"))}; ltx = {t["h"]: t for t in jl(J("w02_ltx_cache.jsonl"))}
def fam(pid):
    i = ini.get(pid)
    if not i: return "older pool"
    t = ltx.get(i["tx"])
    if not t: return f"non-ETH {i['fee']}/{i['ts']}"
    return {2.4333285: "v2.433", 3.0: "v3.0", 5.0: "v5.0"}.get(round(int(t["v"]) / 1e18, 7), f"{round(int(t['v'])/1e18, 7)} {i['fee']}/{i['ts']}")
for target in range(n_now - 1, max(n_lo, n_now - k) - 1, -1):
    lo, hi = lo0, h  # first block where nonce > target
    while lo < hi:
        m = (lo + hi) // 2
        if nonce(m) > target: hi = m
        else: lo = m + 1
    b = get_blocks([lo])[lo]
    for t in b["txs"]:
        if t["f"] == w:
            rc = rpc.call("eth_getTransactionReceipt", [t["h"]])
            sw = [(fam(l["topics"][1]), sgn(W(l["data"], 0)) / 1e18, "0x" + l["topics"][2][-40:][:10]) for l in rc["logs"] if l["address"].lower() == PM and l["topics"][0] == T_SWAP]
            print(lo, utc(b["ts"]), "nonce", t["nonce"], "->", t["to"], t["sel"], t["len"], int(t["v"]) / 1e18, "status", rc["status"], "swaps", sw)
print(rpc.STATS)
