"""Who sends the bot router's buys since the stop: a sample of 1,600 buy transactions (t02, from the PoolManager) spread evenly over time;
tx.from, selector, nonce, value; per 6-hour bin: callers, new callers, the 31 old 2.433 buyers, the old 3.0/5.0 buyer sets (Oct 12 skeptic k09)."""
from common import *
import collections, random
ins = [r for r in jl(J("t02_in_cache.jsonl")) if r["fr"] == PM]
random.seed(7); samp = sorted(random.sample(ins, 1600), key=lambda r: r["b"])
have = {r["h"]: r for r in jl(J("t10_tx_cache.jsonl"))}
need = sorted({r["tx"] for r in samp if r["tx"] not in have})
with open(J("t10_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 20):
        for x in rpc.batch("eth_getTransactionByHash", [[h] for h in need[i:i + 20]], n=20):
            if not x: continue
            r = {"h": x["hash"], "f": x["from"].lower(), "to": (x.get("to") or "").lower(), "sel": x["input"][:10], "nonce": int(x["nonce"], 16), "v": str(int(x["value"], 16)), "b": int(x["blockNumber"], 16)}
            have[r["h"]] = r; f.write(json.dumps(r) + "\n")
k09 = json.load(open("/home/user/v2pons/research/session_oct12/v2433/skeptic/k09_buyers.json"))
print("k09 keys", list(k09)[:10] if isinstance(k09, dict) else type(k09))
old433 = set(k09["callers2433"])
sel = collections.Counter(); to = collections.Counter(); bins = collections.defaultdict(set); nonces = []
for r in samp:
    x = have.get(r["tx"])
    if not x: continue
    sel[x["sel"]] += 1; to[x["to"]] += 1; bins[(x["b"] - 86314100) // 216000].add(x["f"]); nonces.append(x["nonce"])
print("selectors", sel.most_common(5)); print("tx to", to.most_common(5))
print("caller nonce p10/50/90", pct(nonces, .1), pct(nonces, .5), pct(nonces, .9))
seen = set()
for k in sorted(bins):
    s = bins[k]; print("6h-bin", k, "callers", len(s), "new vs earlier bins", len(s - seen), "old 2.433 buyers", len(s & old433)); seen |= s
print(rpc.STATS)
