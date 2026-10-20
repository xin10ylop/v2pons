#!/usr/bin/env python3
"""Do the bot's trading wallets get their ETH inside the deployer's router call (0x7422a284, token create)? Latest launches only (state
is kept ~6,000 blocks): balance of every wallet that trades the pool in its first 200 blocks, at the block before / of the create call."""
import sys, os, json, pickle, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc2 import rpc, batch
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import PM, T_INIT, T_SWAP, logs
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
head = int(rpc("eth_blockNumber", []), 16)
ini = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, head - 4500, head - 300)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ini], n=20)
fam = [(l, t) for l, t in zip(ini, txs) if t and (len(t["input"]) - 2) // 2 == 1444 and t["input"][:10] == "0xac9650d8"]
print("head", head, "PM1444 launches in window", len(fam))
for l, t in fam[:4]:
    b0 = int(l["blockNumber"], 16); dep = t["from"].lower(); pid = l["topics"][1]
    # find the deployer's create call: scan back 40 blocks
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(b0 - 40, b0)], n=20)
    cc = [(int(b["number"], 16), x) for b in blks for x in b["transactions"] if x["from"].lower() == dep and (x["to"] or "").lower() == ROUTER]
    if not cc: print("no create call found", b0); continue
    cb, cx = cc[0]
    sw = logs({"address": PM, "topics": [T_SWAP, pid]}, b0, b0 + 200)
    st = batch([("eth_getTransactionByHash", [x["transactionHash"]]) for x in sw], n=20)
    wal = sorted({x["from"].lower() for x in st if x})
    bal = batch([("eth_getBalance", [w, hex(cb - 1)]) for w in wal] + [("eth_getBalance", [w, hex(cb)]) for w in wal], n=40)
    n = len(wal); d = [(w, int(bal[i], 16) / 1e18, int(bal[n + i], 16) / 1e18) for i, w in enumerate(wal)]
    up = [x for x in d if x[2] - x[1] > 1e-9]
    print(f"launch {b0} dep {dep[:10]} nonce {int(t['nonce'],16)} create call blk {cb} value {int(cx['value'],16)/1e18:.4f} ETH; wallets trading first 200 blocks {n}; "
          f"balance up at the create block: {len(up)}, total +{sum(x[2]-x[1] for x in up):.4f} ETH; examples {[(w[:10], round(a,5), round(b,5)) for w,a,b in up[:5]]}")
