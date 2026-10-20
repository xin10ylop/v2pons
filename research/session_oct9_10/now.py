import time, collections
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
b = rpc("eth_getBlockByNumber", ["latest", False]); head = int(b["number"], 16); tnow = int(b["timestamp"], 16)
lo = head - int(3 * 3600 / 0.103)
inits = []
for a in range(lo, head + 1, 99999):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, a, min(a + 99998, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
print("chain now", time.strftime("%H:%M:%S UTC", time.gmtime(tnow)), "| ETH pools in the last 3 h:", len(inits))
rows = collections.Counter(); last = {}
for l, t in zip(inits, txs):
    if not t: continue
    kind = "original launcher" if t["to"] == ORIG else ("fresh copy (0x2fcb9108)" if t["input"][:10] == "0x2fcb9108" else "other")
    bn = int(l["blockNumber"], 16); hr = time.strftime("%H", time.gmtime(tnow - (head - bn) * 0.103))
    rows[(hr, kind)] += 1; last[kind] = bn
for k in sorted(rows): print("  hour", k[0], "UTC", k[1], rows[k])
for k, bn in last.items(): print("last", k, "about", round((head - bn) * 0.103 / 60, 1), "min ago")
