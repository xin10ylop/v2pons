import json, collections, sys
from chain import *
d = json.load(open("oct8_pools.json"))
op = [p for p in d["pools"] if p["kind"] in ("orig", "copy")]
pick = op[::12][:9]
txs = batch([("eth_getTransactionByHash", [p["tx"]]) for p in pick])
def bal(a, b): return int(rpc("eth_getBalance", [a, hex(b)]), 16)
funders = collections.Counter()
for p, t in zip(pick, txs):
    w = t["from"]; hi = p["block"]; lo = hi - 2_000_000
    if bal(w, lo) > 0: print(p["kind"], w, "funded before the search window"); continue
    while lo + 1 < hi:
        m = (lo + hi) // 2
        if bal(w, m) > 0: hi = m
        else: lo = m
    b = rpc("eth_getBlockByNumber", [hex(hi), True])
    src = [x for x in b["transactions"] if (x.get("to") or "").lower() == w.lower()]
    f = src[0]["from"] if src else "internal (contract call in block %d: %s)" % (hi, ",".join(sorted({x['to'][:10] for x in b['transactions'] if x.get('to')}))[:120])
    funders[f] += 1
    print(p["kind"], "launch", p["block"], "wallet", w[:10], "funded at block", hi, f"({p['block'] - hi} blocks before the launch)", "by", f, "value", (int(src[0]["value"], 16) / 1e18 if src else "?"))
print(funders)
