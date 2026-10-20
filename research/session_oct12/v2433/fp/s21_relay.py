"""Our relay's swaps (PoolManager Swap with sender 0x2abb5653) from 01:30 UTC Oct 12 to the head, with each block's exact time and the pool's
cluster: when was our last 2.4333 trade on chain, and did the relay trade anything after it."""
import json, time
from clusters import load
from common import R, PM, T_SWAP, W, sgn, p
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
meta = json.load(open(p("s01_meta.json"))); pf = {r["pid"]: r for r in load()}
ls = []
for a in range(86290000, meta["head"] + 1, 50000):
    ls += R.logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY[2:]]}, a, min(a + 49999, meta["head"]))
bt = R.batch("eth_getBlockByNumber", [[hex(b), False] for b in sorted({int(l["blockNumber"], 16) for l in ls})])
tm = {int(x["number"], 16): int(x["timestamp"], 16) for x in bt}
print("relay swaps since block 86290000 (about 01:27 UTC):", len(ls))
for l in ls:
    b = int(l["blockNumber"], 16); r = pf.get(l["topics"][1]); a0 = sgn(W(l["data"], 0))
    print("  %s block %d %-4s %.6f ETH  pool launched %s  %s  (+%s)" % (time.strftime("%H:%M:%S", time.gmtime(tm[b])), b, "buy" if a0 < 0 else "sell", abs(a0) / 1e18,
          time.strftime("%H:%M:%S", time.gmtime(r["t"])) if r else "?", r["fam"] if r else l["topics"][1][:12], b - r["b"] if r else "?"))
