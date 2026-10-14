"""BSC: every Uniswap v4 PoolManager (0x28e2ea09) Initialize from a start block to the head (the 48 Club public RPC, which serves
old logs in 5,000-block ranges; publicnode refuses logs older than about 10k blocks), compact rows in t21_bsc_inits_cache.jsonl."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_INIT, W, sgn, unpad, jl, J
PM = "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df"
A0 = int(sys.argv[1]); STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
def call(c, m, p):
    for i in range(10):
        try: time.sleep(0.6); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower() or "timed out" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
h = int(call("bsc", "eth_blockNumber", []), 16)
done = {r["a"] for r in jl(J("t21_done_cache.jsonl"))}
with open(J("t21_bsc_inits_cache.jsonl"), "a") as f, open(J("t21_done_cache.jsonl"), "a") as fd:
    for s in range(A0, h + 1, STEP):
        if s in done: continue
        e = min(h, s + STEP - 1)
        try: L = call("bsc48", "eth_getLogs", [{"address": PM, "fromBlock": hex(s), "toBlock": hex(e), "topics": [T_INIT]}])
        except RuntimeError as ex:
            print("publicnode refused", s, str(ex)[:120], flush=True); raise
        for l in L:
            d = l["data"]
            f.write(json.dumps({"pid": l["topics"][1], "c0": unpad(l["topics"][2]), "c1": unpad(l["topics"][3]), "fee": W(d, 0), "ts": sgn(W(d, 1)),
                                "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtP": W(d, 3), "tick": sgn(W(d, 4)), "b": int(l["blockNumber"], 16), "tx": l["transactionHash"]}) + "\n")
        f.flush()
        if e < h: fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), flush=True)
print("head", h)
