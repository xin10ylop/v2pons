"""Swaps sent by the decoy routers 0x65050a9b and 0xfd1b271f (Swap sender topic), Oct 11 12:00 UTC to the head, cached."""
from common import *
OUT = J("w08_dswaps_cache.jsonl")
done = jl(OUT); last = max([d["b"] for d in done], default=None)
inits = jl(J("w01_inits_cache.jsonl")); start = min(r["b"] for r in inits) if last is None else last + 1
h, th = head()
with open(OUT, "a") as f:
    for a in range(start, h + 1, 50000):
        b = min(a + 49999, h)
        for l in rpc.logs({"address": PM, "topics": [T_SWAP, None, [pad(DECOY_R), pad(FRONT_R2)]]}, a, b):
            d = l["data"]
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "pid": l["topics"][1],
                                "r": "0x" + l["topics"][2][-40:], "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1))}) + "\n")
        print("scanned", a, b, flush=True)
json.dump({"head": h, "head_ts": th}, open(J("w08_meta.json"), "w"))
for r in (DECOY_R, FRONT_R2):
    print(r, "code", len(rpc.call("eth_getCode", [r, "latest"])) // 2 - 1, "nonce", int(rpc.call("eth_getTransactionCount", [r, "latest"]), 16), "bal", int(rpc.call("eth_getBalance", [r, "latest"]), 16) / 1e18)
print(rpc.STATS)
