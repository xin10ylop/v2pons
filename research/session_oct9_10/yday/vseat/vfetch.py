#!/usr/bin/env python3
"""Independent fetch for the seat verifier (not using the pricer's cache): for chosen copy launches, the launch tx + receipt,
the launcher's code at latest (and an attempt at the launch block), full blocks L..L+SCAN, and the pool's Swap/ModifyLiquidity
logs L..L+LOGSPAN. Also our relay's Swap logs on Oct 8 with their receipts (gas).

    python3 vfetch.py <launch_block> [<launch_block> ...]   -> raw/<L>.json
    python3 vfetch.py relay                                   -> raw/relay.json
"""
import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, batch, logs, PM, T_SWAP, T_ML

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw")
POOLS = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/oct8_pools.json"))
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SCAN = 16; LOGSPAN = 2000


def one(L):
    out_path = os.path.join(RAW, f"{L}.json")
    if os.path.exists(out_path):
        return
    p = next(x for x in POOLS["pools"] if x["block"] == L and x["kind"] == "copy")
    tx, rec = batch([("eth_getTransactionByHash", [p["tx"]]), ("eth_getTransactionReceipt", [p["tx"]])])
    code_latest = rpc("eth_getCode", [p["to"], "latest"])
    try:
        code_at = rpc("eth_getCode", [p["to"], hex(L)])
    except Exception as e:
        code_at = "ERR " + str(e)[:200]
    blocks = batch([("eth_getBlockByNumber", [hex(L + k), True]) for k in range(SCAN)])
    lg = logs({"address": PM, "topics": [[T_SWAP, T_ML], p["pid"]]}, L, L + LOGSPAN)
    json.dump({"pool": p, "tx": tx, "rec": rec, "code_latest": code_latest, "code_at_L": code_at, "blocks": blocks, "logs": lg}, open(out_path, "w"))
    print(L, "blocks", len(blocks), "logs", len(lg), file=sys.stderr)


def relay():
    out_path = os.path.join(RAW, "relay.json")
    a, z = POOLS["first"], POOLS["last"]
    lg = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, a, z)
    recs = batch([("eth_getTransactionReceipt", [l["transactionHash"]]) for l in lg])
    blks = batch([("eth_getBlockByNumber", [l["blockNumber"], False]) for l in lg])
    json.dump({"logs": lg, "recs": recs, "blocks": blks}, open(out_path, "w"))
    print("relay swaps", len(lg), file=sys.stderr)


if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    for a in sys.argv[1:]:
        relay() if a == "relay" else one(int(a))
