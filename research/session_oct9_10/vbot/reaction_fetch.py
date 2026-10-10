"""Does the v3.0 deployer pull after an OUTSIDE buy? Data: every pool's Swap + ModifyLiquidity logs [b0, b0+1500] (census: cache_plogs; new
pools: fetched by pid chunks), and the transaction of every buy in [b0, min(pull, b0+WIN)] and of the pull. Cache: reaction_cache.pkl."""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, W, sgn
from fetch import universe
WIN = 400
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
CP = os.path.join(HERE, "reaction_cache.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {"logs": {}, "tx": {}}
def save(): pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
cen, nw = universe()
head = int(rpc("eth_blockNumber", []), 16)
if not all(p["pid"] in C["logs"] for p in cen):
    pl = pickle.load(open(os.path.join(HERE, "..", "others", "cache_plogs.pkl"), "rb"))
    for p in cen:
        C["logs"][p["pid"]] = [(bn, li, t0, snd, d, th) for bn, li, t0, snd, d, th in pl.get(p["pid"], []) if bn <= p["b0"] + 1500]
    del pl; save(); print("census logs from cache_plogs", flush=True)
need = [p for p in nw if p["pid"] not in C["logs"]]
for i in range(0, len(need), 20):
    ch = need[i:i + 20]
    a = min(p["b0"] for p in ch); b = min(head, max(p["b0"] for p in ch) + 1500)
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in ch]]}, a, b)
    for p in ch:
        C["logs"][p["pid"]] = [(int(l["blockNumber"], 16), int(l["logIndex"], 16), l["topics"][0][2:] if l["topics"][0].startswith("0x") else l["topics"][0],
                                l["topics"][2] if len(l["topics"]) > 2 else "", l["data"], l["transactionHash"])
                               for l in ls if l["topics"][1] == p["pid"] and int(l["blockNumber"], 16) <= p["b0"] + 1500]
    save(); print("new logs", i + len(ch), flush=True)
# the transactions: every buy up to the pull / WIN, and the pull
want = []
TS = T_SWAP[2:] if T_SWAP.startswith("0x") else T_SWAP
for p in cen + nw:
    ev = sorted(C["logs"][p["pid"]], key=lambda x: (x[0], x[1]))
    pulls = [x for x in ev if not x[2].endswith(TS[-8:]) and sgn(W(x[4], 2)) < 0]
    pb = pulls[0][0] if pulls else None
    end = min(pb if pb is not None else 10**12, p["b0"] + WIN)
    for x in ev:
        if x[0] > end: break
        if x[2].endswith(TS[-8:]) and s128(W(x[4], 0)) < 0: want.append(x[5])
    if pulls: want.append(pulls[0][5])
want = [h for h in dict.fromkeys(want) if h not in C["tx"]]
print("txs to fetch", len(want), flush=True)
for i in range(0, len(want), 50):
    ch = want[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: C["tx"][h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "sel": t["input"][:10], "len": len(t["input"]) // 2 - 1,
                            "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16), "idx": int(t["transactionIndex"], 16)}
    if (i // 50) % 20 == 0: save(); print(i + len(ch), flush=True)
save(); print("done", len(C["tx"]))
