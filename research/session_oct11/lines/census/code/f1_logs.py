#!/usr/bin/env python3
"""Stage 1: window, v4 Initialize logs (PoolManager), V2 PairCreated / V3 PoolCreated on the three factories, bonding-curve creates."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib2 import *

T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_PAIR = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex()
T_POOL = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_FAC = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"
FAC = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"
V2F = ["0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f", "0x0d1ebb179cdbca88d74c923c4255cb2b17474afd"]
V3F = ["0x1f7d7550b1b028f7571e69a784071f0205fd2efa"]


def compact_log(l):
    return {"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"],
            "addr": l["address"].lower(), "topics": l["topics"], "data": l["data"]}


def window():
    w = jget("window.json")
    if w: return w
    t0 = time.time()
    head = int(rpc("eth_blockNumber", []), 16); head_ts = block_ts(head)
    now = int(time.time()); start_ts = now - 7 * 86400
    a = block_at(start_ts, head)
    w = {"from_block": a, "from_ts": block_ts(a), "head": head, "head_ts": head_ts, "now_at_start": now, "target_from_ts": start_ts}
    jput("window.json", w); timing("window", time.time() - t0); log("window", w); return w


def scan(name, flt, step=100_000):
    w = window(); t0 = time.time()
    done = jl_read(name); a = max([c["b"] for c in done], default=w["from_block"] - 1) + 1
    while a <= w["head"]:
        b = min(a + step - 1, w["head"])
        ls = logs(flt, a, b)
        jl_append(name, [{"a": a, "b": b, "logs": [compact_log(l) for l in ls]}]); log(name, a, b, len(ls)); a = b + 1
    timing(name, time.time() - t0)


if __name__ == "__main__":
    window()
    scan("inits.jsonl", {"address": PM, "topics": [T_INIT]})
    scan("factory.jsonl", {"address": V2F + V3F, "topics": [[T_PAIR, T_POOL]]})
    scan("bonding.jsonl", {"address": FAC, "topics": [T_FAC]})
    log("STATS", STATS)
