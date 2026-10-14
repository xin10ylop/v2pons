"""BSC: the deploy transaction of every token minted to the operator's router since block 127380000 (t24): deployer, its nonce, the value
sent with the deploy. A fresh deployer (nonce <= 12) marks the fresh-wallet line (the 2.433 analogue); aged deployers (nonce 150+) are
the PancakeSwap V2 lines. Rows in t27_dep_cache.jsonl; summary per 2 hours and per nonce class."""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import jl, J
m = sorted({r["tok"]: r for r in jl(J("t24_mints_cache.jsonl"))}.values(), key=lambda r: r["b"])
have = {r["tx"]: r for r in jl(J("t27_dep_cache.jsonl"))}
need = [r["tx"] for r in m if r["tx"] not in have]
with open(J("t27_dep_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 10):
        for x in xrpc.batch("bsc", "eth_getTransactionByHash", [[h] for h in need[i:i + 10]], n=10):
            if not x: continue
            y = {"tx": x["hash"], "f": x["from"].lower(), "nonce": int(x["nonce"], 16), "v": int(x["value"], 16) / 1e18, "b": int(x["blockNumber"], 16), "gas": int(x["gas"], 16)}
            have[y["tx"]] = y; f.write(json.dumps(y) + "\n")
v4 = {i["c1"] for i in jl(J("t21_bsc_inits_cache.jsonl")) if i["fee"] == 5000}
cls = lambda n: "fresh(<=12)" if n <= 12 else ("aged 150-200" if 150 <= n < 200 else ("aged 280-300" if 280 <= n < 300 else "other %d" % (n // 50 * 50)))
per = collections.defaultdict(collections.Counter)
for r in m:
    d = have.get(r["tx"])
    if not d: continue
    k = cls(d["nonce"]) + (" v4-5000" if r["tok"] in v4 else "")
    per[(r["b"] - 127380000) // 16000][k] += 1
for k in sorted(per): print("2h-bin from 127380000 +", k * 16000, dict(per[k]))
fresh = [have[r["tx"]] for r in m if r["tx"] in have and have[r["tx"]]["nonce"] <= 12]
print("fresh deployers:", len(fresh), "blocks", fresh[0]["b"] if fresh else None, "..", fresh[-1]["b"] if fresh else None)
print("fresh deployers not on the v4 fee-5000 line:", [(d["b"], d["f"][:10], d["nonce"]) for r in m for d in [have.get(r["tx"])] if d and d["nonce"] <= 12 and r["tok"] not in v4][:20])
