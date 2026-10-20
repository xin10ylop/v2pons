#!/usr/bin/env python3
"""Verifier step 6 fetch: (a) an independent recount of the census window's Initialize logs (currency0 = 0), in 50,000-block chunks;
(b) every v4 ETH pool launched after the census head (84,238,619) up to now: launch tx, launch contract code hash, Swap + ModifyLiquidity
logs over [launch, launch + 400]. Cache: verify/cache_post.pkl.   python3 v6_fetch.py"""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML
from eth_utils import keccak
START = 82878144; CH = 84238619; SPAN = 400
CP = os.path.join(HERE, "cache_post.pkl")
C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
def save(): pickle.dump(C, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
head = int(rpc("eth_blockNumber", []), 16) - 3
if "recount" not in C:
    ids = []; a = START
    while a <= CH:
        b = min(a + 49999, CH); ids += [l["topics"][1] for l in logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b)]; a = b + 1
    C["recount"] = ids; save(); print("recount", len(ids), flush=True)
post = C.get("post", {"to": CH, "logs": []})
a = post["to"] + 1
while a <= head:
    b = min(a + 49999, head); post["logs"] += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); post["to"] = b; a = b + 1
C["post"] = post; C["head"] = head; save(); print("post pools", len(post["logs"]), "to", post["to"], flush=True)
txs = C.setdefault("txs", {})
need = sorted({l["transactionHash"] for l in post["logs"]} - set(txs))
for i in range(0, len(need), 50):
    ch = need[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: txs[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower() or None, "nonce": int(t["nonce"], 16), "value": int(t["value"], 16) / 1e18, "sel": t["input"][:10],
                        "inlen": (len(t["input"]) - 2) // 2, "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16)}
save(); print("txs", len(txs), flush=True)
codes = C.setdefault("codes", {})
tos = sorted({t["to"] for t in txs.values() if t["to"]} - set(codes))
for i in range(0, len(tos), 20):
    ch = tos[i:i + 20]
    for a_, c in zip(ch, batch([("eth_getCode", [x, "latest"]) for x in ch])):
        if c is not None: codes[a_] = {"hash": keccak(bytes.fromhex(c[2:])).hex() if len(c) > 2 else None, "size": (len(c) - 2) // 2}
save(); print("codes", len(codes), flush=True)
plogs = C.setdefault("plogs", {})
pools = sorted(((int(l["blockNumber"], 16), l["topics"][1]) for l in post["logs"]), key=lambda x: x[0])
todo = [(b, p) for b, p in pools if p not in plogs and b + SPAN <= head]
groups = []; g = []
for b, p in todo:
    if g and (b - g[0][0] > 3000 or len(g) >= 40): groups.append(g); g = []
    g.append((b, p))
if g: groups.append(g)
for gi, g in enumerate(groups):
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p for _, p in g]]}, g[0][0], g[-1][0] + SPAN)
    win = {p: b for b, p in g}; out = {p: [] for _, p in g}
    for x in ls:
        p = x["topics"][1]; bn = int(x["blockNumber"], 16)
        if win[p] <= bn <= win[p] + SPAN: out[p].append((bn, int(x["logIndex"], 16), x["topics"][0], x["topics"][2], x["data"], x["transactionHash"]))
    plogs.update(out)
    if gi % 10 == 0: save(); print("plogs group", gi, len(groups), flush=True)
    time.sleep(0.1)
save(); print("done head", head, "post pools", len(post["logs"]), "with logs", len(plogs))
