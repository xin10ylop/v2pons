"""Data for the exact feed replay of the v2.433 rule: 12 census pools + 8 forward pools + the newest launches (Initialize logs to the head).
Per pool: full blocks b0..b0+SCAN (transactions with input), the pool's Swap/ModifyLiquidity logs over [b0, b0+LOGSPAN]. -> replay_data.pkl"""
import sys, os, pickle, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); EX = os.path.dirname(HERE); SCR = os.path.dirname(EX)
sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; VAL = 2433328500000000000
SCAN = 31; LOGSPAN = 3000
OUT = os.path.join(HERE, "replay_data.pkl")
D = pickle.load(open(OUT, "rb")) if os.path.exists(OUT) else {"pools": {}}
head = int(rpc("eth_blockNumber", []), 16); D["head"] = head
P = pickle.load(open(os.path.join(EX, "pools.pkl"), "rb")); FP = pickle.load(open(os.path.join(EX, "fwd_pools.pkl"), "rb"))
cen = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
fwd = sorted([p for p in FP.values() if "v2.433" in p["fam"]], key=lambda p: p["b0"])
pick = [("census", cen[int(i * (len(cen) - 1) / 11)]) for i in range(12)] + [("forward", fwd[int(i * (len(fwd) - 1) / 7)]) for i in range(8)]
# newest launches: Initialize logs (currency0 = ETH) after the forward set
if "new" not in D:
    L = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, fwd[-1]["b0"] + 1, head - SCAN)
    hs = sorted({l["transactionHash"] for l in L}); tx = {}
    for i in range(0, len(hs), 50):
        for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
            if t: tx[h] = t
        time.sleep(0.3)
    new = []
    for l in L:
        d = l["data"]; t = tx.get(l["transactionHash"])
        if not t: continue
        hooks = d[2 + 64 * 2 + 24: 2 + 64 * 3]
        if (t["to"] or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and W(d, 0) == 2500 and sgn(W(d, 1)) == 50 and int(t["value"], 16) == VAL and hooks == "0" * 40:
            new.append({"pid": l["topics"][1], "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "fee": 2500, "ts": 50,
                        "sp0": W(d, 3), "tick0": sgn(W(d, 4)), "from": t["from"].lower(), "nonce": int(t["nonce"], 16), "txindex": int(l["transactionIndex"], 16)})
    D["new"] = new; D["n_init_after_fwd"] = len(L)
    print("Initialize logs after the forward set:", len(L), "v2.433 among them:", len(new), "blocks", fwd[-1]["b0"] + 1, head - SCAN, flush=True)
pick += [("new", p) for p in D["new"][-6:]]
for src, p in pick:
    pid = p["pid"]
    if pid in D["pools"]: continue
    b0 = p["b0"]
    blocks = batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(SCAN)])
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + LOGSPAN, head))
    rec = rpc("eth_getTransactionReceipt", [p["tx"]])
    D["pools"][pid] = {"src": src, "meta": {k: p.get(k) for k in ("pid", "b0", "tx", "token", "fee", "ts", "sp0", "tick0", "from", "nonce", "txindex")}, "blocks": blocks, "logs": ls, "rec": rec,
                       "logspan_end": min(b0 + LOGSPAN, head)}
    pickle.dump(D, open(OUT, "wb"))
    print(src, pid[:10], b0, "blocks", sum(1 for b in blocks if b), "logs", len(ls), flush=True); time.sleep(0.3)
print("done", len(D["pools"]))
