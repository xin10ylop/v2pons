"""The volume bot router 0x1cbaf24d: every Swap it sent to the PoolManager (sender = router) from Oct 11 12:00 to the head, cached;
its code hash."""
from common import *
OUT = J("w03_rswaps_cache.jsonl"); m = json.load(open(J("w01_meta.json")))
done = jl(OUT); last = max([d["b"] for d in done], default=None)
inits = jl(J("w01_inits_cache.jsonl")); start = min(r["b"] for r in inits) if last is None else last + 1
h, th = head()
with open(OUT, "a") as f:
    for a in range(start, h + 1, 50000):
        b = min(a + 49999, h)
        for l in rpc.logs({"address": PM, "topics": [T_SWAP, None, pad(BOT)]}, a, b):
            d = l["data"]
            f.write(json.dumps({"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "pid": l["topics"][1],
                                "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1)), "fee": W(d, 5)}) + "\n")
        print("scanned", a, b, flush=True)
code = rpc.call("eth_getCode", [BOT, "latest"]); print("router code bytes", (len(code) - 2) // 2, "keccak", keccak(hexstr=code).hex())
json.dump({"head": h, "head_ts": th, "code_len": (len(code) - 2) // 2, "code_hash": keccak(hexstr=code).hex()}, open(J("w03_meta.json"), "w"))
print(rpc.STATS)
