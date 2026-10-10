"""Fetch, for every operator launch on Oct 8 (orig + copy, oct8_pools.json) and the Oct 9 00:11 pool we traded: the Initialize
log, every Swap / ModifyLiquidity on the pool from the launch to launch + 30000 blocks, the transaction of every swap up to the
first pull + 50 blocks (sender, nonce, value, index), the launch tx, and the receipts of our 10 trades. Cache: react_data.json"""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
SP = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
B_END = 83754506                                     # Oct 9 01:00 UTC
SPAN = 30000
D = json.load(open(SP + "/oct8_pools.json"))
pools = {p["pid"]: dict(p) for p in D["pools"] if p["kind"] in ("orig", "copy")}
head = int(rpc("eth_blockNumber", []), 16)
# our relay swaps (to add any traded pool outside Oct 8)
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0"*24 + RELAY]}, D["first"], B_END)
extra = sorted({l["topics"][1] for l in ours} - set(pools))
print("traded pools outside the Oct 8 list:", extra)
for pid in extra:
    b = min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == pid)
    ini = logs({"address": PM, "topics": [T_INIT, pid]}, b - 5000, b)
    t = rpc("eth_getTransactionByHash", [ini[0]["transactionHash"]])
    pools[pid] = {"block": int(ini[0]["blockNumber"], 16), "pid": pid, "tx": ini[0]["transactionHash"], "to": t["to"], "from": t["from"],
                  "kind": "orig" if t["to"][2:].lower() == OP else ("copy" if t["input"][:10] == "0x2fcb9108" else "other"), "fee": W(ini[0]["data"], 0), "oct9": True}
out = {"pools": {}, "ours": ours}
pids = sorted(pools, key=lambda p: pools[p]["block"])
for n, pid in enumerate(pids):
    p = pools[pid]; b0 = p["block"]
    ini = logs({"address": PM, "topics": [T_INIT, pid]}, b0, b0)[0]; d = ini["data"]
    p.update({"token": ini["topics"][3][-40:], "c0": ini["topics"][2][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": d[2+64*2+24:2+64*3], "sqrtP0": W(d, 3), "tick0": sgn(W(d, 4))})
    ev = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + SPAN, head))
    ev.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    pulls = [int(l["blockNumber"], 16) for l in ev if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    lim = (min(pulls) + 50) if pulls else b0 + SPAN
    hs = sorted({l["transactionHash"] for l in ev if int(l["blockNumber"], 16) <= lim} | {p["tx"]})
    txs = batch([("eth_getTransactionByHash", [h]) for h in hs])
    T = {h: {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "nonce": int(t["nonce"], 16), "value": int(t["value"], 16), "idx": int(t["transactionIndex"], 16),
             "sel": t["input"][:10], "bn": int(t["blockNumber"], 16)} for h, t in zip(hs, txs) if t}
    blk = rpc("eth_getBlockByNumber", [hex(b0), False])
    p["ts"] = int(blk["timestamp"], 16); p["base_fee"] = int(blk["baseFeePerGas"], 16)
    out["pools"][pid] = {"meta": p, "ev": [{"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "t0": l["topics"][0], "sender": l["topics"][2][-40:], "data": l["data"], "tx": l["transactionHash"]} for l in ev], "txs": T}
    print(n, pid[:10], p["kind"], b0, "events", len(ev), "txs", len(T), "pull", (min(pulls) - b0) if pulls else None, flush=True)
# our trades' receipts: relay swaps + the router trade (any swap tx sent by the wallet)
hs = sorted({l["transactionHash"] for l in ours} | {h for pid in out["pools"] for h, t in out["pools"][pid]["txs"].items() if t["from"][2:] == WALLET})
recs = batch([("eth_getTransactionReceipt", [h]) for h in hs])
out["receipts"] = {h: {"bn": int(r["blockNumber"], 16), "idx": int(r["transactionIndex"], 16), "status": r["status"], "gasUsed": int(r["gasUsed"], 16), "egp": int(r["effectiveGasPrice"], 16), "from": r["from"], "to": r["to"],
                       "logs": [{"address": l["address"], "topics": l["topics"], "data": l["data"]} for l in r["logs"]]} for h, r in zip(hs, recs)}
# base fee of every block from the launches' first 300 blocks would be a lot; sample the base fee of each trade block instead
bns = sorted({r["bn"] for r in out["receipts"].values()})
out["base_fee"] = {b: int(x["baseFeePerGas"], 16) for b, x in zip(bns, batch([("eth_getBlockByNumber", [hex(b), False]) for b in bns]))}
json.dump(out, open(SP + "/yday/react_data.json", "w"))
print("done", len(out["pools"]), "pools;", len(out["receipts"]), "receipts")
