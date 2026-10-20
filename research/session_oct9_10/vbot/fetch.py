"""Raw chain data for the sampled PM1444 v3.0 pools: the launch receipt, every block b0..b0+SCAN with its full transactions, the pool's
Swap + ModifyLiquidity logs over [b0, b0 + LOGSPAN]. Incremental cache: vbot/cache.pkl (pid -> dict).
    python3 fetch.py N_CENSUS N_NEW     (stratified by time; the census pools first)"""
import sys, os, json, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML
SCAN = 64; LOGSPAN = 1500
CP = os.path.join(HERE, "cache.pkl")
def load():
    return pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
def universe():
    R = [json.loads(l) for l in open(os.path.join(HERE, "..", "others", "census.jsonl"))]
    v3 = [r for r in R if r['sel'] == '0xac9650d8' and r['inlen'] == 1444 and r['fee'] == 10000 and r['ts'] == 200 and round(r['value'] or 0, 3) == 3.0]
    v3 = [{"pid": r["pid"], "b0": r["b0"], "tx": r["tx"], "token": r["token"], "from": r["from"], "nonce": r["nonce"], "src": "census"} for r in v3]
    N = json.load(open(os.path.join(HERE, "new_v3.json")))
    nw = [dict(p, src="new") for p in N["pools"]]
    return sorted(v3, key=lambda r: r["b0"]), sorted(nw, key=lambda r: r["b0"])
def pick(lst, n):
    if n >= len(lst): return lst
    return [lst[int(i * len(lst) / n)] for i in range(n)]
if __name__ == "__main__":
    nc, nn = int(sys.argv[1]), int(sys.argv[2])
    cen, nw = universe()
    head = int(rpc("eth_blockNumber", []), 16)
    nw = [p for p in nw if p["b0"] + SCAN + 5 < head]
    sel = pick(cen, nc) + pick(nw, nn)
    D = load(); t0 = time.time(); k = 0
    for p in sel:
        if p["pid"] in D: continue
        b0 = p["b0"]
        rec = rpc("eth_getTransactionReceipt", [p["tx"]])
        blocks = batch([("eth_getBlockByNumber", [hex(b0 + i), True]) for i in range(SCAN + 1)])
        ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], p["pid"]]}, b0, min(b0 + LOGSPAN, head))
        D[p["pid"]] = {"meta": p, "rec": rec, "blocks": blocks, "logs": ls, "head": head}
        k += 1
        if k % 10 == 0:
            pickle.dump(D, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
            print(f"{k} fetched, {len(D)} in cache, {time.time() - t0:.0f}s", flush=True)
    pickle.dump(D, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
    print("done", len(D), f"{time.time() - t0:.0f}s")
