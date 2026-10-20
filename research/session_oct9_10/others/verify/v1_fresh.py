#!/usr/bin/env python3
"""Verifier step 1: fresh chain data (not the census caches) for sample pools of each claimed family: the Initialize log, the launch tx,
the pool's Swap + ModifyLiquidity logs over [launch, launch + 700], and the transactions behind every swap in [launch, launch + 120]
(who buys/sells, through what, tx value, whether the token address is in the calldata, as the engine detects a buy).
Cache: verify/fresh.pkl.   python3 v1_fresh.py"""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
def full(prefix): return next(p for p in R if p.startswith(prefix))
PICK = {
    "orig": ["0x2701d15ae9", "0x12c952fa9d", "0xda70181865", "0x93950691e9", "0x20a4afb534", "0xc2ac14e543"],
    "copy": ["0x4d57390345", "0xd45759b573"],
    "pm2276": ["0xd2a0677814", "0xe83fb46840", "0xb24d5b37d2", "0xc123feca47", "0xf683fd7bfd", "0xd1a648200f", "0xb8cabf6d7b"],
    "v3": ["0xae0447beab", "0xe594401ff4", "0x4d5ee0b30f", "0x9edbae35c0", "0xe9801cfe15", "0xec4cd7e4d2"],
    "v2433": ["0x6c47407c0b", "0x360912a68f", "0x8dfae21e8d"],
    "v5": ["0x87eb163a8c", "0x6362b6cb69"],
}
extra = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
for k, v in extra.items(): PICK.setdefault(k, []).extend(v)
CP = os.path.join(HERE, "fresh.pkl")
D = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
head = int(rpc("eth_blockNumber", []), 16)
for fam, prefs in PICK.items():
    for pre in prefs:
        pid = full(pre)
        if pid in D: continue
        b0 = R[pid]["b0"]
        init = logs({"address": PM, "topics": [T_INIT, pid]}, b0 - 5, b0 + 5)
        assert len(init) == 1, (pid, len(init))
        h = init[0]["transactionHash"]
        tx = rpc("eth_getTransactionByHash", [h]); rc = rpc("eth_getTransactionReceipt", [h])
        ev = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 700, head))
        ths = sorted({l["transactionHash"] for l in ev if l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) <= b0 + 120})
        txs = {}
        for i in range(0, len(ths), 40):
            ch = ths[i:i + 40]
            for th, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])): txs[th] = t
        mlt = sorted({l["transactionHash"] for l in ev if l["topics"][0] == T_ML})
        for th, t in zip(mlt, batch([("eth_getTransactionByHash", [x]) for x in mlt])): txs[th] = t
        D[pid] = {"fam": fam, "init": init[0], "tx": tx, "rc_status": rc["status"], "rc_logs": len(rc["logs"]), "logs": ev, "txs": txs}
        pickle.dump(D, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
        print("fetched", fam, pid[:12], b0, len(ev), "logs", len(txs), "txs", flush=True)
print("pools", len(D))
