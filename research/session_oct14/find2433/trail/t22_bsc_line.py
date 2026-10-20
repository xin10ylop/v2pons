"""The 2.433 operator's line on BSC (Uniswap v4, PoolManager 0x28e2ea09, PositionManager 0x7a4a5c91, bot router 0x07cb6161):
every native-BNB launch since block 127300000 with the line's fee 5000 / tick spacing 100 (t21), its launch transaction (value, sender,
nonce, calldata length, gas), then per pool every swap in the first 3,000 blocks (Swap logs by pool id) joined with the token Transfer
out of the PoolManager (recipient = the bot router or someone else) and the pull (ModifyLiquidity < 0). Logs from the 48 Club public RPC,
transactions from publicnode. Rows in t22_pools_cache.jsonl."""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import T_SWAP, T_ML, T_TRANSFER, W, sgn, unpad, pad, jl, J, pct
PM = "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df"; ROUTER = "0x07cb61618b69234d954022ff738a015548715533"; ZERO = "0x" + "0" * 40
def call(c, m, p):
    for i in range(10):
        try: time.sleep(0.5); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower() or "timed out" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
inits = [r for r in jl(J("t21_bsc_inits_cache.jsonl")) if r["c0"] == ZERO and r["fee"] == 5000 and r["ts"] == 100 and r["hooks"] == ZERO]
print("native-BNB fee 5000/ts 100 hookless launches:", len(inits), flush=True)
have = {r["pid"]: r for r in jl(J("t22_pools_cache.jsonl"))}
h = int(call("bsc", "eth_blockNumber", []), 16)
with open(J("t22_pools_cache.jsonl"), "a") as f:
    for i in inits:
        if i["pid"] in have and have[i["pid"]].get("final"): continue
        x = call("bsc", "eth_getTransactionByHash", [i["tx"]])
        L = i["b"]; E = min(h, L + 3000)
        sw = call("bsc48", "eth_getLogs", [{"address": PM, "fromBlock": hex(L), "toBlock": hex(E), "topics": [T_SWAP, i["pid"]]}])
        ml = call("bsc48", "eth_getLogs", [{"address": PM, "fromBlock": hex(L), "toBlock": hex(E), "topics": [T_ML, i["pid"]]}])
        tr = call("bsc48", "eth_getLogs", [{"address": i["c1"], "fromBlock": hex(L), "toBlock": hex(E), "topics": [T_TRANSFER, pad(PM)]}])
        rcpt = collections.defaultdict(list)
        for t in tr: rcpt[t["transactionHash"]].append(unpad(t["topics"][2]))
        swaps = [{"b": int(s["blockNumber"], 16), "ix": int(s["logIndex"], 16), "tx": s["transactionHash"], "sender": unpad(s["topics"][2]), "a0": sgn(W(s["data"], 0)), "a1": sgn(W(s["data"], 1)),
                  "to": rcpt.get(s["transactionHash"], [None])[0]} for s in sw]
        mls = [{"b": int(m["blockNumber"], 16), "dl": sgn(W(m["data"], 2))} for m in ml]
        pull = next((m["b"] for m in mls if m["dl"] < 0), None)
        r = {"pid": i["pid"], "tok": i["c1"], "L": L, "sqrtP": i["sqrtP"], "tx": i["tx"], "from": x["from"].lower(), "to": (x.get("to") or "").lower(), "sel": x["input"][:10],
             "len": (len(x["input"]) - 2) // 2, "v": str(int(x["value"], 16)), "nonce": int(x["nonce"], 16), "gas": int(x["gas"], 16), "gp": int(x["gasPrice"], 16),
             "swaps": swaps, "mls": mls, "pull": pull, "final": E < h}
        f.write(json.dumps(r) + "\n"); f.flush(); have[i["pid"]] = r
        print(L, x["from"][:10], int(x["value"], 16) / 1e18, "swaps", len(swaps), "pull", pull and pull - L, flush=True)
print("done")
