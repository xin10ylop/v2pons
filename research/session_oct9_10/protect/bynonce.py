"""Find the transaction a wallet sent with a given nonce: binary search on eth_getTransactionCount(w, block), then the block's txs."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
def nonce_at(w, b): return int(rpc("eth_getTransactionCount", [w, hex(b)]), 16)
def tx_by_nonce(w, k, lo=82000000, hi=None):
    hi = hi or int(rpc("eth_blockNumber", []), 16)
    # smallest block b with nonce_at(w, b) > k
    while lo < hi:
        mid = (lo + hi) // 2
        if nonce_at(w, mid) > k: hi = mid
        else: lo = mid + 1
    blk = rpc("eth_getBlockByNumber", [hex(lo), True])
    for t in blk["transactions"]:
        if t["from"].lower() == w.lower() and int(t["nonce"], 16) == k:
            return lo, int(blk["timestamp"], 16), t
    return lo, int(blk["timestamp"], 16), None
if __name__ == "__main__":
    w = sys.argv[1]
    for k in map(int, sys.argv[2:]):
        b, ts, t = tx_by_nonce(w, k)
        if t: print(k, b, time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "to", t["to"], "sel", t["input"][:10], "value", int(t["value"], 16) / 1e18, "len", (len(t["input"]) - 2) // 2, "gas", int(t["gas"], 16))
        else: print(k, b, "not found")
