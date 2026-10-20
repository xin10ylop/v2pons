#!/usr/bin/env python3
"""Adversarial check of PM1444 v2.433: raw chain data for an exact feed replay on a sample of pools.
Pools: 12 in-window (pools.pkl, stratified over time, incl. the 3 example pools), 6 forward (fwd_pools.pkl), and every family launch
after the forward set up to head-120 (Initialize logs + launch txs). Per pool: launch receipt, blocks b0..b0+SCAN with full txs,
the pool's Swap/ModifyLiquidity logs over [b0, min(b0+3000, head)]. -> adv/cache.pkl"""
import sys, os, json, pickle, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE); SCR = os.path.dirname(EXP)
sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
SCAN = 45; SPAN = 3000
OUT = os.path.join(HERE, "cache.pkl")
D = pickle.load(open(OUT, "rb")) if os.path.exists(OUT) else {}
def fam(to, inlen, fee, ts, v, hooks):
    return to == PM_POS and inlen == 1444 and fee == 2500 and ts == 50 and abs(v - 2.4333285) < 1e-9 and hooks == "0" * 40
P = pickle.load(open(os.path.join(EXP, "pools.pkl"), "rb"))
inw = sorted([p for p in P.values() if p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50
              and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p], key=lambda p: p["b0"])
EX = ["0x6c47407c0b01d8e1d23f3baf9fca4c26d809fac8d9854b7bbd0ca585568e30d5", "0x8fc0b7aa008c7cf1d29599ceb5b7915b2b8773df6796e95696b7d798bd96b954",
      "0x3ed14f58884713f40af17af436bab37c339f3f7d296619c2a8d7720393254904"]
random.seed(11)
chunks = [inw[i * len(inw) // 9:(i + 1) * len(inw) // 9] for i in range(9)]
sel = [random.choice(c) for c in chunks]
sel = [p for p in sel if p["pid"] not in EX] + [P[x] for x in EX if x in P]
FP = pickle.load(open(os.path.join(EXP, "fwd_pools.pkl"), "rb"))
fwd = sorted([p for p in FP.values() if p["fam"].endswith("fee2500|ts50|v2.433")], key=lambda p: p["b0"])
fsel = [fwd[i * len(fwd) // 6] for i in range(6)]
head = int(rpc("eth_blockNumber", []), 16)
# fresh launches after the forward set
start = fwd[-1]["b0"] + 1
L = []; a = start
while a <= head - 120:
    b = min(a + 49999, head - 120); L += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); a = b + 1
hs = sorted({l["transactionHash"] for l in L}); tx = {}
for i in range(0, len(hs), 50):
    for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
        if t: tx[h] = t
fresh = []
for l in L:
    d = l["data"]; t = tx.get(l["transactionHash"])
    if not t: continue
    to = (t["to"] or "").lower(); inlen = (len(t["input"]) - 2) // 2; v = int(t["value"], 16) / 1e18
    if fam(to, inlen, W(d, 0), sgn(W(d, 1)), v, d[2 + 64 * 2 + 24: 2 + 64 * 3]):
        fresh.append({"pid": l["topics"][1], "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": t["from"].lower(), "nonce": int(t["nonce"], 16), "token": "0x" + l["topics"][3][-40:]})
print("head", head, "fresh launches after", start, ":", len(fresh), "of", len(L), "ETH inits", flush=True)
todo = [("inwin", p) for p in sel] + [("fwd", p) for p in fsel] + [("fresh", p) for p in fresh]
for src, p in todo:
    pid = p["pid"]
    if pid in D: continue
    b0 = p["b0"]
    rec = rpc("eth_getTransactionReceipt", [p["tx"]])
    blocks = []
    for i in range(0, SCAN + 1, 15):
        blocks += batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(i, min(SCAN + 1, i + 15))])
    lg = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + SPAN, head))
    D[pid] = {"meta": {"pid": pid, "b0": b0, "tx": p["tx"], "from": p["from"], "nonce": p["nonce"], "token": p["token"], "src": src, "head": head},
              "rec": rec, "blocks": blocks, "logs": lg}
    pickle.dump(D, open(OUT, "wb"))
    print(src, pid[:12], b0, "blocks", sum(1 for b in blocks if b), "txs", sum(len(b["transactions"]) for b in blocks if b), "logs", len(lg), flush=True)
    time.sleep(0.2)
print("done", len(D))
