"""Step 18: T in seconds (block timestamps of the add A and of the fleet's first buy T), and whether the shape existed before the
24.5 h window (fee-500, tick-spacing-1, no-hook ETH-pair inits sent straight to the PoolManager in the 600,000 blocks before it)."""
import collections, statistics
from common import *
pools = [p for p in load_pools() if p["T"] is not None]
bl = sorted({p["add_bn"] for p in pools} | {p["L"] + p["T"] for p in pools} | {p["L"] for p in pools})
ts = dict(zip(bl, [int(b["timestamp"], 16) for b in rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl], n=25)]))
dTA = [ts[p["L"] + p["T"]] - ts[p["add_bn"]] for p in pools]; dTL = [ts[p["L"] + p["T"]] - ts[p["L"]] for p in pools]
dAL = [ts[p["add_bn"]] - ts[p["L"]] for p in pools]
print("seconds A-L", collections.Counter(dAL).most_common(6))
print("seconds T-A", sorted(collections.Counter(dTA).items()))
print("seconds T-L", sorted(collections.Counter(dTL).items()))
print("blocks per second over the window:", round((max(bl) - min(bl)) / (ts[max(bl)] - ts[min(bl)]), 2))
d = jload("s01_inits.json"); start = d["start"]
ls = []
a = start - 600000
while a < start:
    b = min(a + 49999, start - 1); ls += rpc.logs({"address": PM, "topics": [T_INIT, None, ZERO32]}, a, b); a = b + 1
sel = [l for l in ls if W(l["data"], 0) == 500 and sgn(W(l["data"], 1)) == 1 and int(l["data"][2 + 128 + 24: 2 + 192], 16) == 0]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in sel], n=25) if sel else []
direct = [(int(l["blockNumber"], 16), sgn(W(l["data"], 4))) for l, t in zip(sel, txs) if (t.get("to") or "").lower() == PM and (len(t["input"]) - 2) // 2 == 196]
print(f"before the window (blocks {start-600000}..{start-1}): ETH-pair inits {len(ls)}, fee-500/ts-1/no-hook {len(sel)}, direct 196-byte {len(direct)}", direct[-5:])
if direct:
    b = rpc.call("eth_getBlockByNumber", [hex(direct[0][0]), False]); print("earliest such launch block", direct[0][0], "ts", int(b["timestamp"], 16))
print(rpc.STATS)
