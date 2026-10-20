"""BNB Chain Uniswap v4 line with the 2.433 shape (native BNB, fee 5000 / tick spacing 100, no hook), Oct 13: launch transactions,
every Swap / ModifyLiquidity per pool from launch to launch+6000 blocks, and the transaction behind each swap. 48 Club public RPC.
Rows: c18_launches.json, c18_events_cache.jsonl, c18_swaptx_cache.jsonl."""
import sys, json, os, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
PM = "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df"; Z = "0x" + "0" * 40
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
R = [json.loads(l) for l in open("c11_bsc_inits_cache.jsonl")]
L = [r for r in R if r["c0"] == Z and r["hooks"] == Z and (r["fee"], r["ts_"]) == (5000, 100)]
print("launches", len(L), flush=True)
def bget(method, plist):
    try: return rpcx.batch("bsc_h", method, plist, n=10)
    except Exception as e:
        print("batch failed, singles:", str(e)[:80], flush=True); return [rpcx.call("bsc_h", method, p) for p in plist]
if not os.path.exists("c18_launches.json"):
    txs = bget("eth_getTransactionByHash", [[r["tx"]] for r in L]); rcs = bget("eth_getTransactionReceipt", [[r["tx"]] for r in L])
    for r, t, rc in zip(L, txs, rcs):
        r.update({"from": t["from"], "nonce": int(t["nonce"], 16), "to": t["to"], "value": int(t["value"], 16), "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2,
                  "gas": int(t["gas"], 16), "gp": int(t.get("gasPrice", "0x0"), 16), "gasUsed": int(rc["gasUsed"], 16), "ti": int(t["transactionIndex"], 16), "status": rc["status"],
                  "liq": [int(l["data"][2 + 128: 2 + 192], 16) for l in rc["logs"] if l["topics"][0] == T_ML]})
    codes = bget("eth_getCode", [[r["c1"], "latest"] for r in L])
    for r, c in zip(L, codes): r["tok_len"] = (len(c) - 2) // 2; r["tok_hash"] = "0x" + keccak(hexstr=c).hex() if c and len(c) > 2 else None
    json.dump(L, open("c18_launches.json", "w"), indent=1)
L = json.load(open("c18_launches.json"))
EV = "c18_events_cache.jsonl"
if not os.path.exists(EV):
    ids = [r["id"] for r in L]; a, b = min(r["b"] for r in L), max(r["b"] for r in L) + 6000
    with open(EV, "w") as f:
        for s in range(a, b + 1, 5000):
            for l in rpcx.logs("bsc_h", {"address": PM, "topics": [[T_SWAP, T_ML], ids]}, s, min(s + 4999, b)):
                f.write(json.dumps({"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16), "k": "swap" if l["topics"][0] == T_SWAP else "liq",
                                    "id": l["topics"][1], "sender": "0x" + l["topics"][2][-40:], "d": l["data"], "tx": l["transactionHash"]}) + "\n")
            print("events", s, flush=True)
E = [json.loads(l) for l in open(EV)]
print("events", len(E), flush=True)
TX = "c18_swaptx_cache.jsonl"
have = set(json.loads(l)["h"] for l in open(TX)) if os.path.exists(TX) else set()
need = sorted(set(e["tx"] for e in E) - have)
with open(TX, "a") as f:
    for i in range(0, len(need), 50):
        ch = need[i:i + 50]
        for h, t in zip(ch, bget("eth_getTransactionByHash", [[x] for x in ch])):
            if t: f.write(json.dumps({"h": h, "from": t["from"].lower(), "to": (t["to"] or "").lower(), "v": int(t["value"], 16), "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2,
                                      "nonce": int(t["nonce"], 16), "gp": int(t.get("gasPrice", "0x0"), 16), "gas": int(t["gas"], 16), "inp": t["input"][:700]}) + "\n")
        print("txs", i + len(ch), "/", len(need), flush=True)
print("DONE", rpcx.STATS)
