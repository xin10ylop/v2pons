import collections
from chain import *
ORIG = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16); lo0 = head - int(3.2 * 3600 / 0.103)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, lo0, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
ops = [(l, t) for l, t in zip(inits, txs) if t and t["to"] == ORIG]
print("orig launches", len(ops))
tot = rev = 0; rev_early = 0; per = []
for l, t in ops:
    b0 = int(l["blockNumber"], 16); tb = l["topics"][3][-40:].lower()
    sw = logs({"address": PM, "topics": [T_SWAP, l["topics"][1]]}, b0, b0 + 160)
    real = [int(x["blockNumber"], 16) for x in sw if (lambda a: (a - (1 << 256) if a >= 1 << 255 else a))(int(x["data"][2:66], 16)) <= -2e14]
    if not real: continue
    T = real[0]
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(T, T + 6)])
    cand = [(int(b["number"], 16) - T, x) for b in blks if b for x in b["transactions"] if tb in x["input"].lower() and int(x["value"], 16) >= 2 * 10**14]
    recs = batch([("eth_getTransactionReceipt", [x["hash"]]) for _, x in cand])
    for (off, x), r in zip(cand, recs):
        tot += 1
        if r and r["status"] == "0x0":
            rev += 1; rev_early += off <= 3; per.append((l["blockNumber"], off, x["from"][:10], int(x["value"], 16) / 1e18))
print(f"real-size buys carrying the token in T..T+5: {tot}, reverted {rev} ({rev_early} at T+0..T+3)")
for p in per: print("  ", p)
