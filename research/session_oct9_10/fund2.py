import collections
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16); lo0 = head - int(1.5 * 3600 / 0.103)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, lo0, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
ops = [(l, t) for l, t in zip(inits, txs) if t and t["to"] == ORIG][::4][:8]
def bal(a, b): return int(rpc("eth_getBalance", [a, hex(b)]), 16)
funders = collections.Counter()
for l, t in ops:
    w = t["from"]; L = int(l["blockNumber"], 16); hi = L; lo = L - 20000
    try:
        if bal(w, lo) > 0: print(w, "already funded 20000 blocks before"); continue
    except RuntimeError as e:
        print("state not available", str(e)[:60]); break
    while lo + 1 < hi:
        m = (lo + hi) // 2
        if bal(w, m) > 0: hi = m
        else: lo = m
    b = rpc("eth_getBlockByNumber", [hex(hi), True])
    src = [x for x in b["transactions"] if (x.get("to") or "").lower() == w.lower()]
    if src:
        f = src[0]["from"]; v = int(src[0]["value"], 16) / 1e18; n = int(src[0]["nonce"], 16)
    else:
        f = "internal: " + ",".join(sorted({(x.get("to") or "")[:10] + "<-" + x["from"][:10] for x in b["transactions"]}))[:150]; v = "?"; n = "?"
    funders[f] += 1
    print(f"launch {L} wallet {w[:10]} nonce-at-launch {int(t['nonce'],16)} funded {L - hi} blocks before by {f} (nonce {n}) value {v}")
print(funders.most_common())
