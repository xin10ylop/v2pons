"""Step 1: every Initialize on the PoolManager in the last 24 h (+ margin) with currency0 = native ETH; keep fee 500, tick spacing 1,
no hook; fetch the init transactions and keep the ones sent straight to the PoolManager with 196-byte calldata."""
import sys, time
from common import *
head = int(rpc.call("eth_blockNumber", []), 16)
hb = rpc.call("eth_getBlockByNumber", [hex(head), False]); hts = int(hb["timestamp"], 16)
def ts_of(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
target = hts - 86400 - 1800      # 24.5 h back
lo, hi = head - 1_100_000, head
while hi - lo > 50:
    mid = (lo + hi) // 2
    if ts_of(mid) < target: lo = mid
    else: hi = mid
start = lo
print("head", head, hts, "start", start, ts_of(start))
ls = []
step = 50000
a = start
while a <= head:
    b = min(a + step - 1, head)
    ls += rpc.logs({"address": PM, "topics": [T_INIT, None, ZERO32]}, a, b)
    a = b + 1
print("ETH-pair inits", len(ls))
cand = []
for l in ls:
    d = l["data"]
    fee, ts, hook = W(d, 0), sgn(W(d, 1)), "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
    cand.append(dict(pid=l["topics"][1], token="0x" + l["topics"][3][-40:], fee=fee, ts=ts, hook=hook, sqrt0=W(d, 3), tick0=sgn(W(d, 4)),
                     block=int(l["blockNumber"], 16), tx=l["transactionHash"], li=int(l["logIndex"], 16)))
sel = [c for c in cand if c["fee"] == 500 and c["ts"] == 1 and int(c["hook"], 16) == 0]
print("fee500 ts1 nohook", len(sel))
txs = rpc.batch("eth_getTransactionByHash", [[c["tx"]] for c in sel], n=25)
out = []
for c, t in zip(sel, txs):
    c["from"] = t["from"].lower(); c["to"] = (t.get("to") or "").lower(); c["inlen"] = (len(t["input"]) - 2) // 2
    c["nonce"] = int(t["nonce"], 16); c["value"] = int(t["value"], 16); c["sel"] = t["input"][:10]
    out.append(c)
direct = [c for c in out if c["to"] == PM and c["inlen"] == 196]
print("direct 196-B", len(direct))
import collections
print("others by (to, inlen):", collections.Counter((c["to"][:10], c["inlen"]) for c in out if c not in direct).most_common(10))
jdump(dict(head=head, head_ts=hts, start=start, all_fee500=out, direct=direct), "s01_inits.json")
# block timestamps for the direct launches (for hour bucketing)
bl = sorted({c["block"] for c in direct})
bts = rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl], n=25)
jdump({str(b): int(x["timestamp"], 16) for b, x in zip(bl, bts)}, "s01_blockts.json")
print("posts", rpc.STATS)
