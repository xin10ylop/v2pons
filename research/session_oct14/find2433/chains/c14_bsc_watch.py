"""BNB Chain, Oct 12 13:00 UTC to the head (48.club, 5,000-block windows): any Transfer or Approval touching the operator's known addresses
(router copy 0x07cb6161, hub 0x6c3bd8f6, next wallet 0x8b499c5a, admins 0x5b2b20e1/0x0152c954, Binance deposit 0x31c8cf1c, the 20 Ethereum bot buyers)."""
import sys, json, os; sys.path.insert(0, '.'); import rpcx
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; A = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
D = json.load(open("c09_eth_pool.json"))
W = sorted(set(r["from"] for r in D["rows"] if r["k"] == "swap" and r["sel"] in ("0xc1120e3d", "0x24856bc3")))
ADDR = ["0x07cb61618b69234d954022ff738a015548715533", "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d", "0x8b499c5a56d5d0bed60527463bb1de389d6327e1",
        "0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d", "0x0152c954397718abfe4716eb3aaf86903cff3796", "0x31c8cf1c5edf64777d70727a92a6f46b6b794664",
        "0xfac75d23e417ee39c180bbced4c665c9b57b83b2"] + W
P = [pad(a) for a in ADDR]
meta = json.load(open("c11_bsc_meta.json")); start = meta["start"]
OUT = "c14_bsc_watch_cache.jsonl"; M = "c14_bsc_watch_meta.json"
done = json.load(open(M))["done"] if os.path.exists(M) else start - 1
h, _ = rpcx.head("bsc_h")
with open(OUT, "a") as f:
    s = done + 1
    while s <= h:
        e = min(s + 4999, h)
        for flt in ({"topics": [[T, A], P]}, {"topics": [T, None, P]}):
            for l in rpcx.logs("bsc_h", flt, s, e):
                f.write(json.dumps({"b": int(l["blockNumber"], 16), "a": l["address"], "t": l["topics"], "d": l["data"][:130], "tx": l["transactionHash"]}) + "\n")
        f.flush(); json.dump({"done": e}, open(M, "w")); print("scanned", s, e, flush=True); s = e + 1
print("DONE", rpcx.STATS)
