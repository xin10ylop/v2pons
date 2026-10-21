#!/usr/bin/env python3
"""bsc2433_scan.py FROM_BLOCK TO_BLOCK OUT.json: the 2.433 operator's BNB Chain line on Uniswap v4 (PoolManager 0x28e2ea09): every pool
initialized native/token with fee 5000, tick spacing 100 and no hook (its Base and BNB fingerprint, Oct 14-19), its launch transaction
(value, sender, target), and its Swap and ModifyLiquidity logs for 3,000 blocks (22 min at 0.45 s); the Swap's `sender` is the router
(the operator's bot router 0x37dc44b6 vs the rest). Read through rpc-bsc.48.club (logs two days back, 2,000-block ranges)."""
import json, sys, time, urllib.request, concurrent.futures as cf
from eth_utils import keccak
U = "https://rpc-bsc.48.club"; PM = "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
def rpc(m, p):
    err = None
    for i in range(10):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=30))
            if r.get("result") is not None: return r["result"]
            err = r.get("error")
        except Exception as e: err = str(e)
        time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"{m}: {err}")
a0, a1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
pools = {}
for a in range(a0, a1 + 1, 2000):
    for l in rpc("eth_getLogs", [{"address": PM, "topics": [T_INIT], "fromBlock": hex(a), "toBlock": hex(min(a + 1999, a1))}]):
        d = l["data"][2:]; fee = int(d[0:64], 16); ts = int(d[64:128], 16); hook = d[128 + 24:192]
        if l["topics"][2][-40:] == "0" * 40 and fee == 5000 and ts == 100 and hook == "0" * 40:
            pools[l["topics"][1]] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "sqrtP0": int(d[192:256], 16)}
    if (a - a0) // 2000 % 50 == 0: print("blocks %d/%d, pools %d" % (a - a0, a1 - a0, len(pools)), flush=True)
print("fingerprint pools:", len(pools), flush=True)
def fill(item):
    pid, p = item
    t = rpc("eth_getTransactionByHash", [p["tx"]]); p.update(value=int(t["value"], 16) / 1e18, frm=t["from"].lower(), to=(t["to"] or "").lower(), sel=t["input"][:10], nonce=int(t["nonce"], 16))
    ls = []
    for b in range(p["bn"], p["bn"] + 3000, 2000): ls += rpc("eth_getLogs", [{"address": PM, "topics": [[T_SWAP, T_ML], pid], "fromBlock": hex(b), "toBlock": hex(min(b + 1999, p["bn"] + 2999))}])
    p["ev"] = [(int(l["blockNumber"], 16), int(l["logIndex"], 16), "swap" if l["topics"][0] == T_SWAP else "ml", "0x" + l["topics"][2][-40:], l["data"], l["transactionHash"]) for l in ls]
    return pid, p
with cf.ThreadPoolExecutor(3) as ex:
    for n, (pid, p) in enumerate(ex.map(fill, list(pools.items()))):
        if n % 25 == 0: print("pools filled", n, flush=True)
json.dump(pools, open(out, "w")); print("done ->", out, flush=True)
