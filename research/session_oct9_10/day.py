import time, calendar, collections, json
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
a = block_at(calendar.timegm((2026, 10, 8, 0, 0, 0))); z = block_at(calendar.timegm((2026, 10, 9, 0, 0, 0)))
print("Oct 8 blocks", a, z - 1)
inits = []
for x in range(a, z, 99999):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, x, min(x + 99998, z - 1))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
bts = {}
rows = collections.Counter(); out = []
for l, t in zip(inits, txs):
    if not t: continue
    kind = "orig" if t["to"] == ORIG else ("copy" if t["input"][:10] == "0x2fcb9108" else "other")
    bn = int(l["blockNumber"], 16)
    out.append({"block": bn, "pid": l["topics"][1], "tx": l["transactionHash"], "to": t["to"], "from": t["from"], "kind": kind, "fee": W(l["data"], 0)})
json.dump({"first": a, "last": z - 1, "pools": out}, open("oct8_pools.json", "w"))
# hours by interpolation
ta = calendar.timegm((2026, 10, 8, 0, 0, 0))
for p in out:
    hr = int((p["block"] - a) / (z - a) * 24); rows[(hr, p["kind"])] += 1
for h in range(24):
    print(f"  {h:02d} UTC  orig {rows[(h,'orig')]:3d}  copy {rows[(h,'copy')]:3d}  other {rows[(h,'other')]:3d}")
print("totals", collections.Counter(p["kind"] for p in out))
