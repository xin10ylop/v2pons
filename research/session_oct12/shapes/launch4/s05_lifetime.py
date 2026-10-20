"""Every Swap of the 327 pools from the first launch to the head (lists of 100 pool ids per query, 50,000-block chunks), and the transactions of
the swaps after +600. Cache: cache/s05_sw_cache.jsonl, cache/s05_tx_cache.jsonl; writes s05_head.json. Prints per-shape lifetime activity."""
from common import *
import rpc, collections
D = json.load(open(J("s04_pools.json"))); P = D["pools"]
head = int(rpc.call("eth_blockNumber", []), 16); json.dump({"head": head}, open(J("s05_head.json"), "w"))
a0 = min(p["lb"] for p in P)
ids = sorted(p["pid"] for p in P)
have = jl(C("s05_sw_cache.jsonl")); done_to = max([int(l["blockNumber"], 16) for l in have] + [a0 - 1])
# resume: refetch from the last chunk boundary covered
prog = json.load(open(C("s05_prog.json"))) if os.path.exists(C("s05_prog.json")) else {"to": a0 - 1}
seen = {(l["transactionHash"], l["logIndex"]) for l in have}
with open(C("s05_sw_cache.jsonl"), "a") as f:
    for a in range(prog["to"] + 1, head + 1, 50_000):
        b = min(a + 49_999, head)
        n = 0
        for i in range(0, len(ids), 100):
            for l in rpc.logs({"address": PM, "topics": [T_SWAP, ids[i:i + 100]]}, a, b):
                k = (l["transactionHash"], l["logIndex"])
                if k in seen: continue
                seen.add(k); f.write(json.dumps(l) + "\n"); n += 1
        f.flush(); json.dump({"to": b}, open(C("s05_prog.json"), "w"))
        print(f"blocks {a}..{b}: {n} swaps", flush=True)
sw = jl(C("s05_sw_cache.jsonl"))
byp = {p["pid"]: p for p in P}
late = [l for l in sw if int(l["blockNumber"], 16) > byp[l["topics"][1]]["lb"] + 600]
TX = {t["hash"] for t in jl(C("s05_tx_cache.jsonl"))} | {t["hash"] for t in jl(C("s03_tx_cache.jsonl"))}
need = sorted({l["transactionHash"] for l in late} - TX)
print("swaps", len(sw), "after +600", len(late), "txs to fetch", len(need))
with open(C("s05_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 100):
        for t in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 100]], n=20):
            if t: f.write(json.dumps({k: t[k] for k in ("hash", "from", "to", "value", "nonce", "blockNumber", "transactionIndex", "gasPrice")} | {"sel": t["input"][2:10], "n": (len(t["input"]) - 2) // 2}) + "\n")
print(rpc.STATS)
