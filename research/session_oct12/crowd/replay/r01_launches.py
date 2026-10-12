"""v3crowd launches from Oct 10 12:00 UTC to the head: the factory's PoolCreated (fee 100, WETH on one side) -> the creating txs -> those sent
to the V3 PositionManager as a value-0 multicall of 836 bytes (the engine's v3crowd family: target, calldata_len, value_wei) -> decoded
(v3dec.decode_launch_v3: pool by CREATE2, sqrtP, range, L) and checked against the PoolCreated pool. Writes r01_launches.json, r01_meta.json."""
from common import *
import rpc
from v3dec import decode_launch_v3
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
def ts(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
b0 = head - 200000; t0 = ts(b0); bps = 200000 / max(1, th - t0)
lo, hi = max(1, head - int((th - START_TS) * bps * 1.5)), head
while lo < hi:
    m = (lo + hi) // 2
    if ts(m) < START_TS: lo = m + 1
    else: hi = m
start = lo
print(f"head {head} {utc(th)}; start {start} {utc(ts(start))}; {head - start} blocks ({(head - start) / (th - START_TS):.2f} blocks/s)")
pc = []
for a in range(start, head + 1, 200000):
    b = min(a + 199999, head)
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, b)
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"PoolCreated {len(pc)}; fee 100 with WETH {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
import collections
shapes = collections.Counter(); out = []
for l, t in zip(cand, txs):
    if t is None: print("missing tx", l["transactionHash"]); continue
    to = (t.get("to") or "").lower(); n = (len(t["input"]) - 2) // 2; v = int(t["value"], 16)
    if not (to == NPM and t["input"][:10] == "0xac9650d8" and n == 836 and v == 0):
        shapes[(to[:10], t["input"][2:10], n, v > 0)] += 1; continue
    d = decode_launch_v3(bytes.fromhex(t["input"][2:]))
    pool = "0x" + l["data"][-40:]
    if d is None: print("undecoded", l["transactionHash"]); continue
    if "0x" + d["pool"] != pool: print("pool mismatch", l["transactionHash"], d["pool"], pool); continue
    out.append({"pool": pool, "token": "0x" + d["token"], "qs": d["qs"], "lb": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": t["from"].lower(),
                "nonce": int(t["nonce"], 16), "ti": int(t["transactionIndex"], 16), "sqrt_p": d["sqrt_p"], "lo": d["lo"], "hi": d["hi"], "liq": d["liq"],
                "amount0": d["amount0"], "amount1": d["amount1"], "recipient": "0x" + d["recipient"]})
bl = sorted(set(x["lb"] for x in out)); blk = {}
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): blk[b] = int(r["timestamp"], 16)
for x in out: x["ts"] = blk[x["lb"]]
print(f"v3crowd-shaped launches {len(out)} (WETH token0 {sum(x['qs'] == 0 for x in out)}, token1 {sum(x['qs'] == 1 for x in out)}); launch wallets {collections.Counter(x['from'] for x in out).most_common(6)}")
print("other fee-100 WETH launch shapes:", shapes.most_common(12))
print("(hi, L, amount1) variants:", collections.Counter((x["hi"], x["liq"], x["amount1"] if x["qs"] == 0 else x["amount0"]) for x in out).most_common(12))
json.dump(out, open(J("r01_launches.json"), "w")); json.dump({"head": head, "head_ts": th, "start": start, "start_ts": START_TS, "bps": (head - start) / (th - START_TS)}, open(J("r01_meta.json"), "w"))
print("rpc", rpc.STATS)
