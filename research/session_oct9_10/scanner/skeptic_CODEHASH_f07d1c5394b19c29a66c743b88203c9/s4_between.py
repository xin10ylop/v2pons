import json, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blk import get_blocks
BUY="0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"
D=json.load(open("g3_raw.json")); P={p["pid"]:p for p in D["pools"]}
deps={p["launch_from"]:p for p in D["pools"]}
B=get_blocks(list(range(85176380,85176545)))
for bn in sorted(B):
    for t in B[bn]["transactions"]:
        f=t["from"].lower(); to=(t["to"] or "").lower()
        if f==BUY or to==BUY or f in deps or to in deps:
            print(bn, int(t["transactionIndex"],16), f[:12], "->", to[:12], "nonce", int(t["nonce"],16), "val %.6f"%(int(t["value"],16)/1e18), "sel", t["input"][:10], "len", (len(t["input"])-2)//2, t["hash"][:14])
