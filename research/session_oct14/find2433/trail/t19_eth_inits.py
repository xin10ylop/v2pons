"""Ethereum mainnet: every Uniswap v4 PoolManager (0x000000000004444c) Initialize from block 26176700 (Oct 12 13:30 UTC, just before the
2.433 hub's first mainnet launch) to the head, compact rows in t19_eth_inits_cache.jsonl. Public archive endpoint (Blast), 2,000-block chunks."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_INIT, W, sgn, unpad, jl, J
PM = "0x000000000004444c5dc75cb358380d2e3de08a90"
A0 = int(sys.argv[1]) if len(sys.argv) > 1 else 26176700
def call(m, p, c="eth_archive"):
    for i in range(10):
        try: time.sleep(0.6); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower() or "timeout" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
h = int(call("eth_blockNumber", []), 16)
done = {r["a"] for r in jl(J("t19_done_cache.jsonl"))}
with open(J("t19_eth_inits_cache.jsonl"), "a") as f, open(J("t19_done_cache.jsonl"), "a") as fd:
    for s in range(A0, h + 1, 2000):
        if s in done: continue
        e = min(h, s + 1999)
        try: L = call("eth_getLogs", [{"address": PM, "fromBlock": hex(s), "toBlock": hex(e), "topics": [T_INIT]}], c="ethereum")
        except RuntimeError as ex:
            print("publicnode refused", s, str(ex)[:80], "- 10-block chunks on the archive endpoint", flush=True); L = []
            for k in range(s, e + 1, 10): L += call("eth_getLogs", [{"address": PM, "fromBlock": hex(k), "toBlock": hex(min(e, k + 9)), "topics": [T_INIT]}])
        for l in L:
            d = l["data"]
            f.write(json.dumps({"pid": l["topics"][1], "c0": unpad(l["topics"][2]), "c1": unpad(l["topics"][3]), "fee": W(d, 0), "ts": sgn(W(d, 1)),
                                "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtP": W(d, 3), "tick": sgn(W(d, 4)), "b": int(l["blockNumber"], 16), "tx": l["transactionHash"]}) + "\n")
        f.flush()
        if e < h: fd.write(json.dumps({"a": s, "b": e}) + "\n"); fd.flush()
        print(s, e, len(L), flush=True)
print("head", h)
