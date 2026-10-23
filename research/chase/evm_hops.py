#!/usr/bin/env python3
"""evm_hops.py RPC ADDR...: an EOA's money in and out on a chain with no transfer index (Base), from archive state alone: the block of its
first funding (bisect the balance and nonce), and the transaction that funded it (that block's transactions to it; else an internal
transfer, reported as the block); the block of each of its own transactions (bisect the nonce), with the transaction's target and value.
Read-only; the RPC must serve historic state (Base: https://base.gateway.tenderly.co)."""
import json, sys, time, urllib.request


def rpc(url, m, p, tries=6):
    err = None
    for k in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json", "User-Agent": "research"}), timeout=60))
            if "result" in r:
                return r["result"]
            err = r.get("error")
        except Exception as e:
            err = e
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{m}: {str(err)[:100]}")


def first_block(url, lo, hi, pred):
    """the first block in (lo, hi] where pred(block) holds, pred false at lo and true at hi"""
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid
        else:
            lo = mid
    return hi


def hops(url, a, lo=0, max_own=12):
    a = a.lower(); head = int(rpc(url, "eth_blockNumber", []), 16)
    nonce = lambda b: int(rpc(url, "eth_getTransactionCount", [a, hex(b)]), 16)
    bal = lambda b: int(rpc(url, "eth_getBalance", [a, hex(b)]), 16)
    n_now, b_now = nonce(head), bal(head)
    out = {"addr": a, "nonce": n_now, "eth": b_now / 1e18, "own": []}
    # the earliest block with any balance or nonce: search back from the head in doubling steps, then bisect
    step, hi = 50_000, head
    lo = max(lo, head - step)
    while lo > 0 and (bal(lo) > 0 or nonce(lo) > 0):
        hi, step = lo, step * 2
        lo = max(0, head - step)
    fb = first_block(url, lo, hi, lambda b: bal(b) > 0 or nonce(b) > 0)
    blk = rpc(url, "eth_getBlockByNumber", [hex(fb), True])
    fund = [t for t in blk["transactions"] if (t.get("to") or "").lower() == a]
    out["funded"] = {"block": fb, "t": int(blk["timestamp"], 16), "eth": bal(fb) / 1e18,
                     "by": [(t["from"].lower(), int(t["value"], 16) / 1e18, t["hash"]) for t in fund] or "internal (a contract sent it)"}
    if fund == [] and blk["transactions"]:
        # an internal transfer: name the transactions in that block whose target is a contract we can later read
        out["funded"]["block_txs"] = len(blk["transactions"])
    # each of its own transactions: the block where the nonce passes k
    prev = fb - 1
    for k in range(min(n_now, max_own)):
        b = first_block(url, prev, head, lambda x: nonce(x) > k)
        bb = rpc(url, "eth_getBlockByNumber", [hex(b), True])
        t = next((t for t in bb["transactions"] if t["from"].lower() == a and int(t["nonce"], 16) == k), None)
        out["own"].append({"k": k, "block": b, "t": int(bb["timestamp"], 16), "to": (t.get("to") or "").lower() if t else None,
                           "eth": int(t["value"], 16) / 1e18 if t else None, "sel": t["input"][:10] if t else None, "hash": t["hash"] if t else None})
        prev = b - 1
    return out


if __name__ == "__main__":
    url = sys.argv[1]
    for a in sys.argv[2:]:
        r = hops(url, a)
        f = r["funded"]
        print(f"== {a} nonce {r['nonce']} now {r['eth']:.4f} ETH; funded block {f['block']} {time.strftime('%m-%d %H:%M:%S', time.gmtime(f['t']))} "
              f"by {f['by'] if isinstance(f['by'], str) else [(x[0], round(x[1], 4)) for x in f['by']]}", flush=True)
        for o in r["own"]:
            print(f"   tx{o['k']} {time.strftime('%m-%d %H:%M:%S', time.gmtime(o['t']))} -> {o['to']} {o['eth']} {o['sel']}", flush=True)
