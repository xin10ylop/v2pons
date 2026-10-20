"""launches9.py + fetch9.py for the operator's launches after oct9_pools.json's last block (84115823) up to the head: writes
oct9b_pools.json and react9b_data.json (same shapes)."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
ORIG = "0x" + OP; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
SPAN = 30000
a = 84115824; head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
pl = []
for l, t in zip(inits, txs):
    if not t: continue
    kind = "orig" if (t["to"] or "").lower() == ORIG else ("copy" if t["input"][:10] == "0x2fcb9108" else "other")
    pl.append({"block": int(l["blockNumber"], 16), "pid": l["topics"][1], "tx": l["transactionHash"], "to": (t["to"] or "").lower(), "from": t["from"].lower(), "kind": kind, "fee": W(l["data"], 0),
               "sel": t["input"][:10], "nonce": int(t["nonce"], 16)})
json.dump({"first": a, "last": head, "pools": pl}, open(HERE + "oct9b_pools.json", "w"))
print("head", head, collections.Counter(p["kind"] for p in pl), flush=True)
pools = {p["pid"]: dict(p) for p in pl if p["kind"] in ("orig", "copy")}
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, a, head)
out = {"pools": {}, "ours": ours, "head": head}
for n, pid in enumerate(sorted(pools, key=lambda p: pools[p]["block"])):
    p = pools[pid]; b0 = p["block"]
    ini = logs({"address": PM, "topics": [T_INIT, pid]}, b0, b0)[0]; d = ini["data"]
    p.update({"token": ini["topics"][3][-40:], "c0": ini["topics"][2][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": d[2+64*2+24:2+64*3], "sqrtP0": W(d, 3), "tick0": sgn(W(d, 4))})
    ev = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + SPAN, head))
    ev.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    pulls = [int(l["blockNumber"], 16) for l in ev if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    lim = (min(pulls) + 50) if pulls else head
    hs = sorted({l["transactionHash"] for l in ev if int(l["blockNumber"], 16) <= lim} | {p["tx"]})
    txs = batch([("eth_getTransactionByHash", [h]) for h in hs])
    T = {}; FP = {}
    for h, t in zip(hs, txs):
        if not t: continue
        inp = t["input"]
        T[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "nonce": int(t["nonce"], 16), "value": int(t["value"], 16), "idx": int(t["transactionIndex"], 16),
                "sel": inp[:10], "bn": int(t["blockNumber"], 16)}
        dl = inp[10+128:10+192] if inp[:10] == "0x3593564c" and len(inp) >= 10 + 192 else None
        FP[h] = {"type": int(t["type"], 16), "gas": int(t["gas"], 16), "prio": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "gp": int(t.get("gasPrice", "0x0"), 16),
                 "len": (len(inp) - 2) // 2, "dl_max": dl == "f" * 64 if dl else None, "dl": int(dl, 16) if dl and dl != "f" * 64 else None}
    blk = rpc("eth_getBlockByNumber", [hex(b0), False])
    p["ts"] = int(blk["timestamp"], 16); p["base_fee"] = int(blk["baseFeePerGas"], 16)
    out["pools"][pid] = {"meta": p, "ev": [{"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "t0": l["topics"][0], "sender": l["topics"][2][-40:], "data": l["data"], "tx": l["transactionHash"]} for l in ev],
                         "txs": T, "fp": FP}
    print(n, pid[:10], p["kind"], b0, "events", len(ev), "txs", len(T), "pull", (min(pulls) - b0) if pulls else None, flush=True)
json.dump(out, open(HERE + "react9b_data.json", "w"))
print("done", len(out["pools"]))
