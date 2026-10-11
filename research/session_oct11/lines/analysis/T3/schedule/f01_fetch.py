"""SUPERSEDED by f01_logs.py (aborted: the bot router calls the Universal Router, so no Swap has the bot router as sender; this run found 0).
Schedule angle, step 1 (public RPC, read-only). Last N hours:
 - every ERC-20 Transfer from the PoolManager to the volume bot's router 0x1cbaf24d, any token (the bot's buys and its pulls' token leg,
   all lines, all pools; the router calls the Universal Router, so the Swap's sender is the UR and cannot be filtered on),
 - every ETH-pair Initialize; the launch tx of each pool the bot bought in and of every 3.0/2.4333/5.0-shaped launch,
 - for each bot-served pool launched in the window: every Swap/ModifyLiquidity to L+400 and the txs of its first 120 blocks,
 - the transactions of every bot buy and pull.
-> raw.json (+ txcache.jsonl)"""
import sys, json, time
from eth_utils import keccak
from rpc import rpc, logs, batch, TxCache
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
SPAN = 400
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); PMT = "0x" + "0" * 24 + PM[2:]
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
BOTT = "0x" + "0" * 24 + BOT[2:]
head = int(rpc("eth_blockNumber", []), 16) - 30
hb = None
while hb is None:
    hb = rpc("eth_getBlockByNumber", [hex(head), False])
    if hb is None: head -= 20
th = int(hb["timestamp"], 16)
t1 = int(rpc("eth_getBlockByNumber", [hex(head - 50000), False])["timestamp"], 16)
bps = 50000 / max(1, th - t1)
start = head - int(hours * 3600 * bps)
print(f"head {head} {time.strftime('%m-%d %H:%M:%S', time.gmtime(th))} UTC, {bps:.3f} blocks/s, start {start}", flush=True)
STEP = 10000
botsw, inits = [], []
for a in range(start - 2000, head + 1, STEP):
    b = min(a + STEP - 1, head)
    botsw += logs({"topics": [T_TR, PMT, BOTT]}, a, b)
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b)
    print(f"  {a}-{b}: PM->bot transfers {len(botsw)}, ETH inits {len(inits)}", flush=True)
txc = TxCache("txcache.jsonl")
bot_tokens = set(x["address"].lower() for x in botsw)
SP = {1604517591721945638372359205383840, 679394651928963067279918579724198}
cand = [l for l in inits if ("0x" + l["topics"][3][-40:]) in bot_tokens or (W(l["data"], 2) == 0 and W(l["data"], 3) in SP)]
bot_pids = set(l["topics"][1] for l in cand if ("0x" + l["topics"][3][-40:]) in bot_tokens)
print(f"bot-served pool ids {len(bot_pids)}; candidate launches in window {len(cand)}", flush=True)
lt = txc.get([l["transactionHash"] for l in cand])
pools = []
for l in cand:
    tx = lt.get(l["transactionHash"]) or {}
    d = l["data"]
    pools.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "lb": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16),
                  "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"], "fee": W(d, 0), "tsp": sgn(W(d, 1)), "hooks": W(d, 2), "sp0": W(d, 3),
                  "to": (tx.get("to") or "").lower(), "value": int(tx.get("value") or "0x0", 16), "clen": (len((tx.get("input") or "0x")) - 2) // 2,
                  "from": (tx.get("from") or "").lower(), "nonce": int(tx["nonce"], 16) if tx.get("nonce") else None, "sel": (tx.get("input") or "")[2:10],
                  "bot_served": l["topics"][1] in bot_pids})
pools.sort(key=lambda p: (p["lb"], p["li"]))
print(f"{len(pools)} pools; by (to POSM, value, clen): " + str(sorted(__import__('collections').Counter((p['to'] == POSM, p['value'] / 1e18, p['clen'], p['bot_served']) for p in pools).items())), flush=True)
# per-pool swap/ML to L+400 (groups of overlapping windows)
ev = {p["pid"]: {"sw": [], "ml": []} for p in pools}
i = 0
while i < len(pools):
    j = i
    while j + 1 < len(pools) and pools[j + 1]["lb"] - pools[i]["lb"] < 3000 and j + 1 - i < 40: j += 1
    grp = pools[i:j + 1]; ids = [p["pid"] for p in grp]; byid = {p["pid"]: p for p in grp}
    a, b = grp[0]["lb"], min(head, grp[-1]["lb"] + SPAN)
    for topic, key in ((T_SWAP, "sw"), (T_ML, "ml")):
        for x in logs({"address": PM, "topics": [topic, ids]}, a, b):
            p = byid[x["topics"][1]]; bn = int(x["blockNumber"], 16)
            if p["lb"] <= bn <= p["lb"] + SPAN:
                ev[p["pid"]][key].append({"bn": bn, "li": int(x["logIndex"], 16), "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"],
                                          "sender": "0x" + x["topics"][2][-40:], "data": x["data"]})
    i = j + 1
print("per-pool logs fetched", flush=True)
hs = [x["transactionHash"] for x in botsw]
for p in pools:
    for k in ("sw", "ml"):
        hs += [e["tx"] for e in ev[p["pid"]][k] if e["bn"] - p["lb"] <= 150 or k == "ml"]
hs = list(dict.fromkeys(hs))
print(f"fetching {len(hs)} transactions", flush=True)
txc.get(hs)
def slim(x): return {"token": x["address"].lower(), "amt": int(x["data"], 16), "bn": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16), "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"], "data": x["data"]}
json.dump({"head": head, "head_ts": th, "bps": bps, "start": start, "hours": hours, "pools": pools, "ev": ev,
           "bottr": [slim(x) for x in botsw]}, open("raw.json", "w"))
print("done", flush=True)
