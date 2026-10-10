import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, batch, logs, PM, T_SWAP, W, sgn
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, 82878144, 83740000)
recs = batch([("eth_getTransactionReceipt", [l["transactionHash"]]) for l in ls])
out = []
for l, r in zip(ls, recs):
    a0 = s128(W(l["data"], 0)); a1 = s128(W(l["data"], 1))
    out.append({"block": int(l["blockNumber"], 16), "tx": l["transactionHash"], "pid": l["topics"][1], "a0": a0, "a1": a1, "status": r["status"], "gasUsed": int(r["gasUsed"], 16),
                "egp": int(r["effectiveGasPrice"], 16), "from": r["from"], "to": r["to"], "idx": int(r["transactionIndex"], 16)})
for o in out: print(o["block"], o["tx"][:12], o["pid"][:10], "buy " if o["a0"] < 0 else ("sell" if o["a0"] > 0 else "zero"), o["a0"], o["a1"], o["status"], o["gasUsed"], o["egp"], o["idx"])
json.dump(out, open("relay_swaps.json", "w"), indent=0)
