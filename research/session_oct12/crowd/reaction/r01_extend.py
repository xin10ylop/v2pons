"""extend r01_launches.json back in time: the factory's PoolCreated from block START to the current first block - 1, same filter as
r01_launches.py (the line's 836-byte value-0 PositionManager multicall, decoded by W/v3dec.py), merged in; the head in r01_meta.json is
kept (windows of the pools already fetched do not move). Scans back in 400k-block steps from the current start until STOP_EMPTY steps
in a row hold no line launch (the line's beginning) or START is reached."""
from common import *
import rpc, collections
from v3dec import decode_launch_v3
START = int(sys.argv[1]) if len(sys.argv) > 1 else 70_000_000
L = json.load(open(J("r01_launches.json"))); M = json.load(open(J("r01_meta.json")))
b_hi = M["start"] - 1; step = 400_000; empty = 0; new = []; other = collections.Counter()
while b_hi >= START and empty < 3:
    a = max(START, b_hi - step + 1)
    pc = rpc.logs({"address": FACT, "topics": [T_PC]}, a, b_hi)
    cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
    txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
    got = 0
    for l, t in zip(cand, txs):
        to = (t.get("to") or "").lower() if t else ""; n = (len(t["input"]) - 2) // 2 if t else 0; v = int(t["value"], 16) if t else -1
        d = decode_launch_v3(bytes.fromhex(t["input"][2:])) if t and to == NPM and n == 836 and v == 0 else None
        if not d: other[(to[:10], t["input"][:10] if t else None, n, v > 0)] += 1; continue
        pool = "0x" + l["data"][-40:]
        if pool[2:] != d["pool"]: continue
        new.append({"pool": pool, "token": "0x" + d["token"], "qs": d["qs"], "lb": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"],
                    "from": t["from"].lower(), "nonce": int(t["nonce"], 16), "sqrt_p": d["sqrt_p"], "hi": d["hi"], "lo": d["lo"], "liq": d["liq"], "a1": d["amount1"], "a0": d["amount0"],
                    "rcpt": "0x" + d["recipient"]}); got += 1
    print(f"blocks {a}-{b_hi}: PoolCreated {len(pc)}, fee-100 WETH {len(cand)}, line launches {got}", flush=True)
    empty = empty + 1 if got == 0 else 0
    b_hi = a - 1
bl = sorted(set(x["lb"] for x in new)); ts = {}
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): ts[b] = int(r["timestamp"], 16)
for x in new: x["ts"] = ts[x["lb"]]
have = {x["pool"] for x in L}; add = [x for x in new if x["pool"] not in have]
L = sorted(L + add, key=lambda x: (x["lb"], x["ti"]))
M["start"] = b_hi + 1
json.dump(L, open(J("r01_launches.json"), "w")); json.dump(M, open(J("r01_meta.json"), "w"))
days = collections.Counter(time.strftime('%m-%d', time.gmtime(x['ts'])) for x in add)
print(f"added {len(add)} launches; total {len(L)}; first {utc(L[0]['ts'])}; per day added {sorted(days.items())}")
print("rpc", rpc.STATS)
