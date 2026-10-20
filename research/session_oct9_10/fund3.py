import collections
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16); lo0 = head - int(1.5 * 3600 / 0.103)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, lo0, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
ops = [(l, t) for l, t in zip(inits, txs) if t and t["to"] == ORIG][::5][:5]
funders = collections.Counter()
for l, t in ops:
    w = t["from"].lower(); L = int(l["blockNumber"], 16); found = None
    for end in range(L, L - 6000, -100):
        bs = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(end - 99, end + 1)])
        for b in reversed(bs):
            for x in (b or {}).get("transactions", []):
                if (x.get("to") or "").lower() == w and int(x["value"], 16) > 0:
                    found = (int(b["number"], 16), x); break
            if found: break
        if found: break
    if found:
        bn, x = found; f = x["from"]; funders[f] += 1
        print(f"launch {L} wallet {w[:10]} funded {L - bn} blocks before by {f} (its nonce {int(x['nonce'],16)}) with {int(x['value'],16)/1e18:.6f} ETH")
    else:
        print(f"launch {L} wallet {w[:10]}: no direct ETH transfer in the 6000 blocks before (internal transfer or earlier)")
print(funders.most_common())
