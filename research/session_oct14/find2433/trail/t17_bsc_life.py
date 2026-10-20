"""A Robinhood 2.433 wallet's life on BSC: binary search on its BSC nonce through the public archive endpoint (Blast public API; publicnode
BSC refuses archive reads), then the transaction at each nonce (block, to, selector, value, logs summary). Read-only, paced 1 s."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
xrpc_post = xrpc.post
def call(m, p, chain="bsc_archive"):
    for i in range(8):
        try:
            time.sleep(0.5); return xrpc.call(chain, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e): time.sleep(5 * (i + 1)); continue
            raise
    raise RuntimeError("gave up")
w = sys.argv[1].lower(); lo0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
h = int(call("eth_blockNumber", []), 16)
nonce = lambda b: int(call("eth_getTransactionCount", [w, hex(b)]), 16)
n_now = nonce(h); print(w, "BSC nonce now", n_now, "head", h, flush=True)
lo_b = lo0 or h - 115200 * 120                                    # about 120 days back at 0.75 s blocks
out = []
prev = lo_b
for target in range(n_now):
    lo, hi = prev, h                                              # first block where nonce > target
    while lo < hi:
        m = (lo + hi) // 2
        if nonce(m) > target: hi = m
        else: lo = m + 1
    prev = lo
    b = call("eth_getBlockByNumber", [hex(lo), True], chain="bsc")
    for t in b["transactions"]:
        if t["from"].lower() == w:
            rc = call("eth_getTransactionReceipt", [t["hash"]])
            logs = [(l["address"], l["topics"][0][:10], len(l["topics"])) for l in rc["logs"]][:8]
            r = {"nonce": int(t["nonce"], 16), "b": lo, "ts": int(b["timestamp"], 16), "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(int(b["timestamp"], 16))), "to": t.get("to"), "sel": t["input"][:10],
                 "len": (len(t["input"]) - 2) // 2, "v": int(t["value"], 16) / 1e18, "status": rc["status"], "nlogs": len(rc["logs"]), "logs": logs, "h": t["hash"]}
            out.append(r); print(json.dumps(r), flush=True)
json.dump(out, open("/home/user/v2pons/research/session_oct14/find2433/trail/t17_bsc_%s.json" % w[:10], "w"), indent=0)
