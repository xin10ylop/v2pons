"""Re-fetch Robinhood-chain txs by hash: from, to, value, nonce, block, time, status."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
hs = [h for h in sys.argv[1:]]
txs = batch([("eth_getTransactionByHash", [h]) for h in hs])
rcs = batch([("eth_getTransactionReceipt", [h]) for h in hs])
bns = sorted({int(t["blockNumber"], 16) for t in txs if t})
bl = dict(zip(bns, batch([("eth_getBlockByNumber", [hex(b), False]) for b in bns])))
for h, t, r in zip(hs, txs, rcs):
    if not t: print(h, "NOT FOUND"); continue
    b = int(t["blockNumber"], 16); ts = int(bl[b]["timestamp"], 16)
    print(json.dumps({"hash": h[:18], "block": b, "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "from": t["from"], "to": t["to"], "eth": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16), "type": t["type"], "sel": t["input"][:10], "inlen": len(t["input"]) // 2 - 1, "status": r["status"] if r else None}))
