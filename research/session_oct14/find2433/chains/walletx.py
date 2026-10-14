"""Reconstruct an EOA's outgoing transactions on a chain without an indexer: binary-search the blocks where its nonce changes
(historical eth_getTransactionCount), then read those blocks. Read-only, public endpoints."""
import sys, json; sys.path.insert(0, '/home/user/v2pons/research/session_oct14/find2433/chains'); import rpcx
def nonce(ch, a, b): return int(rpcx.call(ch, "eth_getTransactionCount", [a, hex(b)]), 16)
def bal(ch, a, b): return int(rpcx.call(ch, "eth_getBalance", [a, hex(b)]), 16)
def first_block_with_nonce_gt(ch, a, k, lo, hi):
    # smallest b in (lo, hi] with nonce(b) > k ; assumes nonce(lo) <= k < nonce(hi)
    while hi - lo > 1:
        m = (lo + hi) // 2
        if nonce(ch, a, m) > k: hi = m
        else: lo = m
    return hi
def txs(ch, a, lo, hi):
    a = a.lower(); n0 = nonce(ch, a, lo); n1 = nonce(ch, a, hi); out = []
    k = n0; cur = lo
    while k < n1:
        b = first_block_with_nonce_gt(ch, a, k, cur, hi)
        blk = rpcx.call(ch, "eth_getBlockByNumber", [hex(b), True])
        mine = [t for t in blk["transactions"] if t["from"].lower() == a]
        for t in mine:
            out.append({"b": b, "ts": int(blk["timestamp"], 16), "h": t["hash"], "nonce": int(t["nonce"], 16), "to": t.get("to"), "v": int(t["value"], 16) / 1e18,
                        "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2, "input": t["input"][:2000]})
        k = max(k + 1, max([int(t["nonce"], 16) + 1 for t in mine], default=k + 1)); cur = b
    return n0, n1, out
