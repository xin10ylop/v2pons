#!/usr/bin/env python3
"""deployer.py RPC ADDR...: who deployed a contract (archive RPC): bisect eth_getCode by block for the creation block, then that block's
receipts (contractAddress) or, for a contract made by another contract, the transactions to known factories in it (reported raw)."""
import sys, time
import evm_hops as H


def created(url, a):
    head = int(H.rpc(url, "eth_blockNumber", []), 16)
    has = lambda b: len(H.rpc(url, "eth_getCode", [a, hex(b)])) > 2
    lo = 0
    b = H.first_block(url, lo, head, has)
    blk = H.rpc(url, "eth_getBlockByNumber", [hex(b), True])
    for t in blk["transactions"]:
        if t.get("to") is None:
            r = H.rpc(url, "eth_getTransactionReceipt", [t["hash"]])
            if (r.get("contractAddress") or "").lower() == a.lower():
                return b, int(blk["timestamp"], 16), t["from"].lower(), int(t["nonce"], 16), t["hash"], "create"
    # made by a contract: find the transaction whose receipt has a log from the new contract or whose trace we cannot read
    for t in blk["transactions"]:
        r = H.rpc(url, "eth_getTransactionReceipt", [t["hash"]])
        if any(l["address"].lower() == a.lower() for l in r["logs"]):
            return b, int(blk["timestamp"], 16), t["from"].lower(), int(t["nonce"], 16), t["hash"], "via " + (t.get("to") or "")
    return b, int(blk["timestamp"], 16), None, None, None, f"{len(blk['transactions'])} txs, not found"


if __name__ == "__main__":
    url = sys.argv[1]
    for a in sys.argv[2:]:
        b, t, frm, n, h, how = created(url, a)
        print(f"{a}: block {b} {time.strftime('%y-%m-%d %H:%M', time.gmtime(t))} by {frm} nonce {n} ({how}) tx {h}", flush=True)
