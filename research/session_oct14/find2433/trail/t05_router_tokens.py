"""Classify every token minted to the bot router since the stop (t02) by its launch: the Initialize (t04) where it is currency1 against
ETH, and the launch transaction (value, sender, nonce, to, selector, calldata length, gas). Rows in t05_ltx_cache.jsonl; table to stdout."""
from common import *
import collections
ins = jl(J("t02_in_cache.jsonl"))
mints = {r["tok"]: r for r in ins if r["fr"] == ZERO}
inits = jl(J("t04_inits_cache.jsonl"))
by_tok = collections.defaultdict(list)
for i in inits:
    by_tok[i["c1"]].append(i); by_tok[i["c0"]].append(i)
have = {r["h"]: r for r in jl(J("t05_ltx_cache.jsonl"))}
need = []
for t in mints:
    for i in by_tok.get(t, []):
        if i["tx"] not in have: need.append(i["tx"])
need = sorted(set(need)); print("launch txs to fetch", len(need), flush=True)
with open(J("t05_ltx_cache.jsonl"), "a") as f:
    for k in range(0, len(need), 20):
        res = rpc.batch("eth_getTransactionByHash", [[x] for x in need[k:k + 20]], n=20)
        for x in res:
            if not x: continue
            r = {"h": x["hash"], "f": x["from"].lower(), "to": (x.get("to") or "").lower(), "v": str(int(x["value"], 16)), "nonce": int(x["nonce"], 16),
                 "sel": x["input"][:10], "len": (len(x["input"]) - 2) // 2, "gas": int(x["gas"], 16), "b": int(x["blockNumber"], 16)}
            have[r["h"]] = r; f.write(json.dumps(r) + "\n")
print(rpc.STATS)
