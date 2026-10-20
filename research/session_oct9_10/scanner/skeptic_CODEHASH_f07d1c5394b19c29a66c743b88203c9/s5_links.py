import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import load_pools
from blk import get_blocks
P=load_pools()
D=json.load(open("g3_raw.json")); G=D["pools"]
deps=set(p["launch_from"] for p in G)
byfrom=collections.defaultdict(list)
for p in P.values(): byfrom[p["launch_from"]].append(p)
other=[(p["launch_from"],p["launch_nonce"],p["family"],p["to_code_hash"],p["launch_block"]) for d in deps for p in byfrom[d] if not (p.get("to_code_hash") or "").startswith("f07d1c53")]
print("other census pools by these deployers:", len(other)); 
for o in other[:20]: print(" ", o)
# token transfer recipients in the cached blocks
B=get_blocks(list(range(85176380,85176545)))
for bn in sorted(B):
    for t in B[bn]["transactions"]:
        if t["input"].startswith("0xa9059cbb"):
            f=t["from"].lower()
            if f in deps or f=="0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a":
                print(bn, f[:12], "token", t["to"], "-> to 0x"+t["input"][34:74], "amt", int(t["input"][74:138],16))
