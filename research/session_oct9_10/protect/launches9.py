"""Every ETH-paired v4 pool initialised from Oct 9 00:00 UTC (block 83719339) to the head, with its launch tx; kind orig (tx to the
original launcher), copy (call 0x2fcb9108), other. Writes oct9_pools.json (same shape as ../oct8_pools.json)."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
ORIG = "0x" + OP
a = 83719339; head = int(rpc("eth_blockNumber", []), 16)
inits = []
for x in range(a, head + 1, 99999):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, x, min(x + 99998, head))
print("inits", len(inits), flush=True)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
out = []
for l, t in zip(inits, txs):
    if not t: print("missing tx", l["transactionHash"]); continue
    kind = "orig" if (t["to"] or "").lower() == ORIG else ("copy" if t["input"][:10] == "0x2fcb9108" else "other")
    out.append({"block": int(l["blockNumber"], 16), "pid": l["topics"][1], "tx": l["transactionHash"], "to": (t["to"] or "").lower(), "from": t["from"].lower(), "kind": kind, "fee": W(l["data"], 0),
                "sel": t["input"][:10], "nonce": int(t["nonce"], 16)})
json.dump({"first": a, "last": head, "pools": out}, open(HERE + "oct9_pools.json", "w"))
import collections
print("head", head, collections.Counter(p["kind"] for p in out))
