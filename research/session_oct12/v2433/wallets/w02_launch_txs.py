"""The launch transaction of every ETH-quoted Initialize in w01 (from, to, value, calldata length, nonce, gas), cached in w02_ltx_cache.jsonl;
block timestamps for those blocks in w02_bts_cache.jsonl."""
from common import *
rows = [r for r in jl(J("w01_inits_cache.jsonl")) if r["c0"] == "0x" + "0" * 40]
OUT = J("w02_ltx_cache.jsonl"); have = {d["h"] for d in jl(OUT)}
need = sorted({r["tx"] for r in rows} - have)
print(len(rows), "ETH inits;", len(need), "txs to fetch")
with open(OUT, "a") as f:
    for i in range(0, len(need), 100):
        ch = need[i:i + 100]
        for hsh, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[x] for x in ch], n=20)):
            if not t: continue
            f.write(json.dumps({"h": hsh, "f": t["from"].lower(), "to": (t.get("to") or "").lower(), "v": str(int(t["value"], 16)), "nonce": int(t["nonce"], 16),
                                "len": (len(t["input"]) - 2) // 2, "sel": t["input"][:10], "gp": int(t.get("gasPrice", "0x0"), 16), "tip": int(t.get("maxPriorityFeePerGas", "0x0"), 16),
                                "mf": int(t.get("maxFeePerGas", "0x0"), 16), "gas": int(t["gas"], 16), "type": t.get("type"), "b": int(t["blockNumber"], 16),
                                "inp": t["input"] if len(t["input"]) < 6000 else t["input"][:6000]}) + "\n")
        print(i + len(ch), flush=True)
# timestamps: one per 200 blocks bucket is enough for hour bins; exact for the 2.433-price launches
BT = J("w02_bts_cache.jsonl"); bts = {d["b"]: d["ts"] for d in jl(BT)}
want = sorted({r["b"] for r in rows if r["sqrtP"] == SQRTP_2433} | {r["b"] - r["b"] % 2000 for r in jl(J("w01_inits_cache.jsonl"))})
need = [b for b in want if b not in bts]
with open(BT, "a") as f:
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]
        for b, blk in zip(ch, rpc.batch("eth_getBlockByNumber", [[hex(x), False] for x in ch], n=20)):
            if blk: f.write(json.dumps({"b": b, "ts": int(blk["timestamp"], 16)}) + "\n")
print(rpc.STATS)
