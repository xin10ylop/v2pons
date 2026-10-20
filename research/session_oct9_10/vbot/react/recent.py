#!/usr/bin/env python3
"""Launches since the census head (84238619) to now: every v4 ETH pool Initialize, its launch tx, PM1444 family classification.
Writes recent.json (pid, b0, ts, family, deployer, nonce, value, fee)."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, batch, logs, PM, T_INIT, W, sgn
A = 84238620; head = int(rpc("eth_blockNumber", []), 16)
L = []; a = A
while a <= head:
    b = min(a + 99999, head); L += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); a = b + 1
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in L])
bl = sorted({int(l["blockNumber"], 16) for l in L})
ts = {}
for i in range(0, len(bl), 50):
    for n, x in zip(bl[i:i+50], batch([("eth_getBlockByNumber", [hex(n), False]) for n in bl[i:i+50]])): ts[n] = int(x["timestamp"], 16)
out = []
for l, t in zip(L, txs):
    d = l["data"]; fee = W(d, 0); tsp = sgn(W(d, 1)); hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
    inlen = (len(t["input"]) - 2) // 2; v = int(t["value"], 16) / 1e18; sel = t["input"][:10]
    fam = None
    if sel == "0xac9650d8" and inlen == 1444 and int(hooks, 16) == 0:
        if fee == 10000 and tsp == 200 and round(v, 3) == 3.0: fam = "v3.0"
        elif fee == 10000 and tsp == 200 and round(v, 3) == 5.0: fam = "v5.0"
        elif fee == 2500 and tsp == 50: fam = "v2.433"
        else: fam = f"pm1444-other fee{fee} ts{tsp} v{round(v,3)}"
    bn = int(l["blockNumber"], 16)
    out.append({"pid": l["topics"][1], "b0": bn, "ts": ts[bn], "fam": fam, "deployer": t["from"].lower(), "nonce": int(t["nonce"], 16), "value": v, "fee": fee, "tsp": tsp,
                "to": (t["to"] or "").lower(), "tx": t["hash"], "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "token": "0x" + l["topics"][3][-40:] if False else None})
json.dump({"from": A, "head": head, "head_ts": int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16), "launches": out}, open(os.path.join(HERE, "recent.json"), "w"))
import collections
print("head", head, "pools", len(out), collections.Counter(x["fam"] for x in out).most_common(8))
