"""A wallet's most recent k transactions inside the node's state window (about 4,800 blocks): binary search on the nonce, then the
block's tx and receipt; prints to, selector, value, status, and the v4 Swap / Transfer logs it emitted."""
from common import *
w = sys.argv[1].lower(); k = int(sys.argv[2]) if len(sys.argv) > 2 else 4
h, th = head(); lo0 = h - 4700
nonce = lambda b: int(rpc.call("eth_getTransactionCount", [w, hex(b)]), 16)
n_now, n_lo = nonce(h), nonce(lo0)
print(w, "nonce now", n_now, "4700 blocks ago", n_lo, "at", utc(th), "balance", int(rpc.call("eth_getBalance", [w, "latest"]), 16) / 1e18)
for target in range(n_now - 1, max(n_lo, n_now - k) - 1, -1):
    lo, hi = lo0, h
    while lo < hi:
        m = (lo + hi) // 2
        if nonce(m) > target: hi = m
        else: lo = m + 1
    b = rpc.call("eth_getBlockByNumber", [hex(lo), True])
    for t in b["transactions"]:
        if t["from"].lower() == w:
            rc = rpc.call("eth_getTransactionReceipt", [t["hash"]])
            sw = []
            for l in rc["logs"]:
                if l["address"].lower() == PM and l["topics"][0] == T_SWAP:
                    sw.append(("swap", l["topics"][1][:14], "sender", unpad(l["topics"][2])[:10], sgn(W(l["data"], 0)) / 1e18, sgn(W(l["data"], 1))))
                elif l["topics"][0] == T_TRANSFER and len(l["topics"]) == 3:
                    sw.append(("xfer", l["address"][:10], unpad(l["topics"][1])[:10], unpad(l["topics"][2])[:10]))
            print(lo, utc(int(b["timestamp"], 16)), "nonce", int(t["nonce"], 16), "->", (t.get("to") or "")[:12], t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16) / 1e18, "st", rc["status"], "logs", len(rc["logs"]), sw[:6], t["hash"])
print(rpc.STATS)
