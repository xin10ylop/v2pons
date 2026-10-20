"""C-1 launches over the last H hours (default 36): Initialize on the PoolManager with fee 100, tick spacing 1, currency0 = ETH, sent to the
v4 PositionManager as a 2,276-byte call with value 0. Writes c01_launches.json (+ c01_meta.json with the head and the start block)."""
from common import *
import rpc
H = float(sys.argv[1]) if len(sys.argv) > 1 else 36
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
def ts(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
target = th - int(H * 3600); lo, hi = head - int(H * 3600 * 12), head
while lo < hi:
    m = (lo + hi) // 2
    if ts(m) < target: lo = m + 1
    else: hi = m
start = lo
print(f"head {head} {utc(th)}; start {start} {utc(ts(start))} ({head - start} blocks, {(head - start) / (th - target):.2f} blocks/s)")
ls = []
for a in range(start, head + 1, 100000):
    ls += rpc.logs({"address": PM, "topics": [T_INIT]}, a, min(a + 99999, head))
cand = [l for l in ls if W(l["data"], 0) == 100 and W(l["data"], 1) == 1 and l["topics"][2][-40:] == "0" * 40]
print(f"Initialize logs {len(ls)}; fee 100 / ts 1 / ETH {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
blk = {}
out = []
for l, tx in zip(cand, txs):
    to = (tx.get("to") or "").lower() if tx else ""; n = (len(tx["input"]) - 2) // 2 if tx else 0; v = int(tx["value"], 16) if tx else -1
    if not (to == POSM and n == 2276 and v == 0): continue
    out.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": tx["from"].lower(),
                "sqrtP": W(l["data"], 3), "tick": sgn(W(l["data"], 4)), "hooks": "0x" + l["data"][2 + 64 * 2 + 24: 2 + 64 * 3]})
bl = sorted(set(x["lb"] for x in out))
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): blk[b] = int(r["timestamp"], 16)
for x in out: x["ts"] = blk[x["lb"]]
import collections
print(f"C-1 launches: {len(out)}; launch wallets {collections.Counter(x['from'] for x in out).most_common(5)}; sqrtP == SQRTP {sum(x['sqrtP'] == SQRTP for x in out)}; hooks {collections.Counter(x['hooks'] for x in out).most_common(3)}")
json.dump(out, open(J("c01_launches.json"), "w")); json.dump({"head": head, "head_ts": th, "start": start, "start_ts": ts(start), "H": H}, open(J("c01_meta.json"), "w"))
print("rpc", rpc.STATS)
