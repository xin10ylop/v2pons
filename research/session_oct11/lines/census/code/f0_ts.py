#!/usr/bin/env python3
"""Block timestamp grid (every 5,000 blocks over the window, plus the head) for interpolating launch times."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *
if __name__ == "__main__":
    w = window(); g = jget("tsgrid.json", {})
    bns = list(range(w["from_block"], w["head"] + 6000, 5000))
    head = int(rpc("eth_blockNumber", []), 16); bns = [b for b in bns if b <= head] + [head]
    need = [b for b in bns if str(b) not in g]
    r = batch([("eth_getBlockByNumber", [hex(b), False]) for b in need], size=50)
    for b, x in zip(need, r):
        if x: g[str(b)] = int(x["timestamp"], 16)
    jput("tsgrid.json", g); log("grid", len(g), STATS)
