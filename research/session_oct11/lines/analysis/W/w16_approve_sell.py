"""Do sellers on this chain put the token approval and the sell in one block with consecutive nonces? For sells (WETH out) in the line's
pools over the last 8 h through SwapRouter02 / the Universal Router: the block of the sell, and the seller's other transactions in it
and in the block before (approve 095ea7b3 to the token at nonce - 1?)."""
import json, sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from v3dec import WETH
D = json.load(open("w05_recent_8h.json"))
sells = []
for x in D["line"]:
    qs = 0 if x["token0"] == "0x" + WETH else 1; tok = x["token1"] if qs == 0 else x["token0"]
    for l in x["logs"]:
        if l["topics"][0][2:10] != "c42079f9": continue
        d = l["data"]; a = int(d[2 + 64 * qs: 2 + 64 * (qs + 1)], 16); a = a - (1 << 256) if a >> 255 else a
        if a < 0 and l["topics"][1][-40:] in ("caf681a66d020601342297493863e78c959e5cb2", "8876789976decbfcbbbe364623c63652db8c0904"):
            sells.append((l["transactionHash"], tok, int(l["blockNumber"], 16)))
print("sells whose Swap sender is SwapRouter02 or the UR", len(sells)); import random; random.seed(1); random.shuffle(sells)
sells = sells[:40]
txs = rpc.batch("eth_getTransactionByHash", [[h] for h, _, _ in sells])
cand = [(s, t) for s, t in zip(sells, txs) if t]
print("sell txs by (to, selector, len):", Counter((t["to"][:10], t["input"][:10], (len(t["input"]) - 2) // 2) for _, t in cand).most_common(6))
blocks = sorted({s[2] for s, _ in cand[:25]} | {s[2] - 1 for s, _ in cand[:25]})
B = dict(zip(blocks, rpc.batch("eth_getBlockByNumber", [[hex(b), True] for b in blocks], n=10)))
res = Counter()
for (h, tok, bn), t in cand[:25]:
    me = t["from"].lower(); n = int(t["nonce"], 16); found = None
    for b in (bn, bn - 1):
        for tx in B[b]["transactions"]:
            if tx["from"].lower() == me and int(tx["nonce"], 16) == n - 1:
                found = ("same block" if b == bn else "block before", tx["to"].lower() == tok, tx["input"][:10], int(tx["transactionIndex"], 16), int(t["transactionIndex"], 16))
    res[str(found[:3]) if found else "nonce-1 not within 1 block"] += 1
    if found and found[0] == "same block": print("  ", h[:12], "approve idx", found[3], "sell idx", found[4], "to token", found[1], found[2])
for k, v in res.most_common(): print(v, k)
print(rpc.STATS)
