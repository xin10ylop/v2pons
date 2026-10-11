"""Chain, last N hours: every 2.4333 / 3.0 ETH launch of the volume bot (PositionManager multicall, 1,444 bytes), and for each pool every
Swap and ModifyLiquidity log to launch + 400 blocks, every transaction of those logs (from/to/nonce/input). -> chain_raw.json, txcache.jsonl"""
import sys, json, time
from eth_utils import keccak
from rpc import rpc, logs, batch, TxCache
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
SPAN = 400
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SP = {1604517591721945638372359205383840: "2.433", 679394651928963067279918579724198: "3.0"}
VAL = {2433328500000000000: "2.433", 3 * 10 ** 18: "3.0"}
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x

head = int(rpc("eth_blockNumber", []), 16) - 20      # a load-balanced node may lag the one that answered
hb = None
while hb is None:
    hb = rpc("eth_getBlockByNumber", [hex(head), False])
    if hb is None: head -= 20
th = int(hb["timestamp"], 16)
t1 = int(rpc("eth_getBlockByNumber", [hex(head - 20000), False])["timestamp"], 16)
bps = 20000 / max(1, th - t1)
start = head - int(hours * 3600 * bps)
print(f"head {head} {time.strftime('%H:%M:%S', time.gmtime(th))} UTC, {bps:.2f} blocks/s, start {start}", flush=True)
inits = []
for a in range(start, head + 1, 5000):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, min(a + 4999, head))
cand = []
for l in inits:
    d = l["data"]; fee, ts, hooks, sp = W(d, 0), sgn(W(d, 1)), W(d, 2), W(d, 3)
    if hooks == 0 and sp in SP: cand.append((l, fee, ts, sp))
print(f"{len(inits)} ETH-pair initializes, {len(cand)} at a line's launch price", flush=True)
txc = TxCache("txcache.jsonl")
lt = txc.get([l["transactionHash"] for l, *_ in cand])
pools = []
for l, fee, ts, sp in cand:
    tx = lt.get(l["transactionHash"])
    if not tx: continue
    v = int(tx["value"], 16); clen = (len(tx["input"]) - 2) // 2
    if (tx.get("to") or "").lower() != POSM or v not in VAL: continue
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][2 + 1][-40:], "lb": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
                  "line": VAL[v], "fee": fee, "ts_": ts, "sp0": sp, "clen": clen, "from": tx["from"], "nonce": int(tx["nonce"], 16)})
print(f"{len(pools)} line launches: " + ", ".join(f"{k} {sum(1 for p in pools if p['line'] == k)}" for k in ("2.433", "3.0")), flush=True)
# launch block timestamps
bl = sorted(set(p["lb"] for p in pools))
hdr = batch([("eth_getBlockByNumber", [hex(b), False]) for b in bl])
bts = {b: int(h["timestamp"], 16) for b, h in zip(bl, hdr) if h}
for p in pools: p["ts"] = bts.get(p["lb"])
# swaps and liquidity logs in groups of pools whose windows overlap
pools.sort(key=lambda p: p["lb"])
ev = {p["pid"]: {"sw": [], "ml": []} for p in pools}
i = 0
while i < len(pools):
    j = i
    while j + 1 < len(pools) and pools[j + 1]["lb"] - pools[i]["lb"] < 3000 and j + 1 - i < 40: j += 1
    grp = pools[i:j + 1]; ids = [p["pid"] for p in grp]
    a, b = grp[0]["lb"], min(head, grp[-1]["lb"] + SPAN)
    for topic, key in ((T_SWAP, "sw"), (T_ML, "ml")):
        for x in logs({"address": PM, "topics": [topic, ids]}, a, b):
            p = next(pp for pp in grp if pp["pid"] == x["topics"][1])
            bn = int(x["blockNumber"], 16)
            if p["lb"] <= bn <= p["lb"] + SPAN:
                ev[x["topics"][1]][key].append({"bn": bn, "li": int(x["logIndex"], 16), "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"],
                                                "sender": "0x" + x["topics"][2][-40:], "data": x["data"]})
    print(f"  pools {i}-{j}: blocks {a}-{b}", flush=True)
    i = j + 1
hs = [e["tx"] for p in pools for k in ("sw", "ml") for e in ev[p["pid"]][k]]
print(f"{len(hs)} logs; fetching {len(set(hs))} transactions", flush=True)
txc.get(hs)
json.dump({"head": head, "head_ts": th, "bps": bps, "start": start, "hours": hours, "pools": pools, "ev": ev}, open("chain_raw.json", "w"))
print("done", flush=True)
