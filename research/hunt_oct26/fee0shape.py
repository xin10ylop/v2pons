#!/usr/bin/env python3
"""fee0shape.py HOURS: what the engine would see of the fee-0 family in the feed: the launch call (to, selector, length, value, the target's
full code keccak), and for the first buys and sells after the launch block, each transaction's to, selector, length, ETH value and whether the
token's address is in its calldata (the follow entry finds buys that way). Read-only."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, watchfee0 as W
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24; SP = 2505036234966386302045715536678303
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
init = W.getlogs(head - int(HOURS * 36000), head - 300, [W.T_INIT4], W.PM)
fam = [(l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"], l["topics"][3][-40:]) for l in init if l["topics"][2] == "0x" + "0" * 64
       and int(l["data"][2:][128 + 24:192], 16) == 0 and int(l["data"][2:][0:64], 16) == 0 and H.i256(l["data"][2:][64:128]) == 60 and int(l["data"][2:][192:256], 16) == SP]
print(f"{len(fam)} launches in {HOURS:g} h")
launch = collections.Counter(); codes = collections.Counter(); buys = collections.Counter(); sells = collections.Counter(); tok_in = collections.Counter()
for pid, bn, h, tok in fam:
    t = H.rpc(url, "eth_getTransactionByHash", [h])
    c = H.rpc(url, "eth_getCode", [t["to"], "latest"])
    codes["0x" + keccak(bytes.fromhex(c[2:])).hex() if len(c) > 2 else "none"] += 1
    launch[(t["input"][:10], (len(t["input"]) - 2) // 2, round(int(t["value"], 16) / 1e18, 2))] += 1
    sw = W.getlogs(bn + 1, bn + 2000, [W.T_SWAP4, pid], W.PM)[:40]
    txs = H.batch(url, [("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw], size=40, workers=4, tries=8)
    for s, x in zip(sw, txs):
        if not x:
            continue
        buy = W.sg(s["data"][2:66]) < 0
        k = (x["to"][:10], x["input"][:10], "value>0" if int(x["value"], 16) else "value=0")
        (buys if buy else sells)[k] += 1
        tok_in[("buy" if buy else "sell", tok in x["input"].lower())] += 1
print("launch call (selector, length, value):", launch.most_common(6))
print("launcher code keccak:", codes.most_common(3))
print("buys (to, selector, value):", buys.most_common(8))
print("sells (to, selector, value):", sells.most_common(8))
print("token address in calldata (side, yes/no):", sorted(tok_in.items()))
