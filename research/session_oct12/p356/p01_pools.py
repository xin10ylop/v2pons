"""p01: every Uniswap V3 PoolCreated (factory 0x1f7d7550) over the last 48 hours, the creating tx of each, and the keccak of each tx's `to`
code (eth_getCode at latest). Read-only, public RPC, polite pacing (rpc.py = a copy of analysis/W/rpc.py).
-> p01_meta.json (window, time grid), p01_pools.jsonl (one row per PoolCreated), p01_txs.jsonl (creating txs), p01_code.json (to -> code keccak, size)"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rpc
from eth_utils import keccak
FACTORY = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
T_CREATED = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
WETH = "0bd7d308f8e1639fab988df18a8011f41eacad73"
J = lambda n: os.path.join(HERE, n)


def bts(b):
    return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)


def block_at(ts, lo, hi):
    while hi - lo > 1:
        m = (lo + hi) // 2
        if bts(m) <= ts: lo = m
        else: hi = m
    return lo


if os.path.exists(J("p01_meta.json")):
    meta = json.load(open(J("p01_meta.json")))
else:
    H = int(rpc.call("eth_blockNumber", []), 16); TH = bts(H)
    B0 = block_at(TH - 48 * 3600, H - 1_900_000, H)
    grid = {}
    for b in list(range(B0, H, 25_000)) + [H]:
        grid[b] = bts(b)
    meta = {"head": H, "head_ts": TH, "from": B0, "from_ts": grid[B0], "grid": grid}
    json.dump(meta, open(J("p01_meta.json"), "w"))
H, B0 = meta["head"], meta["from"]
print("window", B0, H, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(meta["from_ts"])), time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(meta["head_ts"])))

if not os.path.exists(J("p01_pools.jsonl")):
    rows = []
    for a in range(B0, H + 1, 100_000):
        b = min(H, a + 99_999)
        for l in rpc.logs({"address": FACTORY, "topics": [T_CREATED]}, a, b):
            d = l["data"][2:]
            rows.append({"block": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "token0": l["topics"][1][-40:],
                         "token1": l["topics"][2][-40:], "fee": int(l["topics"][3], 16), "ts_spacing": int(d[0:64], 16) - (1 << 256 if int(d[0:64], 16) >> 255 else 0),
                         "pool": d[64 + 24:128]})
        print("logs to", b, len(rows), flush=True)
    with open(J("p01_pools.jsonl"), "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
rows = [json.loads(x) for x in open(J("p01_pools.jsonl"))]
print("PoolCreated", len(rows), "WETH pools", sum(1 for r in rows if WETH in (r["token0"], r["token1"])))

have = {}
if os.path.exists(J("p01_txs.jsonl")):
    for x in open(J("p01_txs.jsonl")):
        t = json.loads(x); have[t["hash"]] = t
need = sorted(set(r["tx"] for r in rows) - set(have))
for i in range(0, len(need), 100):
    res = rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20)
    with open(J("p01_txs.jsonl"), "a") as f:
        for t in res:
            if t is None: continue
            t = {k: t.get(k) for k in ("hash", "from", "to", "input", "value", "nonce", "blockNumber", "maxPriorityFeePerGas", "maxFeePerGas", "gasPrice", "gas", "type", "transactionIndex")}
            have[t["hash"]] = t; f.write(json.dumps(t) + "\n")
    print("txs", len(have), flush=True)

code = json.load(open(J("p01_code.json"))) if os.path.exists(J("p01_code.json")) else {}
tos = sorted(set((have[r["tx"]]["to"] or "").lower() for r in rows if r["tx"] in have) - set(code) - {""})
for i in range(0, len(tos), 40):
    res = rpc.batch("eth_getCode", [[a, "latest"] for a in tos[i:i + 40]], n=20)
    for a, c in zip(tos[i:i + 40], res):
        bc = bytes.fromhex((c or "0x")[2:])
        code[a] = {"hash": keccak(bc).hex() if bc else None, "size": len(bc)}
    json.dump(code, open(J("p01_code.json"), "w"))
print("codes", len(code), "rpc", rpc.STATS)
