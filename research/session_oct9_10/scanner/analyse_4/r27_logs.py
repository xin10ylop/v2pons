#!/usr/bin/env python3
"""Every PoolManager Swap whose sender (topics[2]) is the fresh-wallet router 0x27fad47c, over the census window (any currency0),
and every Swap whose sender is the 0xfcd18241 family's swap contract 0xd809ec17 (check that nobody trades that hook's pools)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import logs, T_SWAP, PM, W, sgn
A, Bk = 83_520_210, 85_203_897
out = {}
for name, addr in (("r27", "27fad47c0abef79bfe44830f170ec0724ded5d12"), ("d809", "d809ec1791774f86c960534009cd11b3292a5bdf")):
    fn = os.path.join(HERE, "cache", f"swaps_{name}.json")
    if os.path.exists(fn):
        L = json.load(open(fn))
    else:
        L = []
        for a in range(A, Bk + 1, 100_000):
            L += logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + addr]}, a, min(a + 99_999, Bk))
        json.dump(L, open(fn, "w"))
    pools = collections.Counter(l["topics"][1] for l in L)
    a0 = [sgn(W(l["data"], 0)) for l in L]
    print(name, "swaps", len(L), "pools", len(pools), "buys(a0<0)", sum(1 for x in a0 if x < 0), "zero", sum(1 for x in a0 if x == 0),
          "blocks", (min(int(l["blockNumber"], 16) for l in L), max(int(l["blockNumber"], 16) for l in L)) if L else None)
    out[name] = {"swaps": len(L), "pools": dict(pools)}
json.dump(out, open(os.path.join(HERE, "r27_logs.json"), "w"), indent=1)
