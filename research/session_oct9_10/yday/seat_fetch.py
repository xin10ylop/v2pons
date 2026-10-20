#!/usr/bin/env python3
"""Fetch (and cache) the chain data the seat pricer needs for every Oct 8 launch of kind "copy" in oct8_pools.json:
the launcher copy's code at the launch block, the launch receipt, every block L..L+SCAN with its transactions (the feed replay),
the pool's Swap/ModifyLiquidity logs L..L+LOG_SPAN, the transactions behind those swaps, and our relay's swaps/receipts on the day.

    python3 seat_fetch.py          -> cache_seat.pkl next to this file
"""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SCRATCH = os.path.dirname(HERE)
sys.path.insert(0, SCRATCH)
from chain import rpc, batch, logs, PM, T_SWAP, T_ML

RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
SCAN = 61            # full blocks L..L+60 (the trade needs L..L+12; the rest is for the burst/early-buyer reading)
LOG_SPAN = 60000     # pool logs L..L+60000 (~1.7 h) for the pull
CACHE = os.path.join(HERE, "cache_seat.pkl")


def main():
    D = json.load(open(os.path.join(SCRATCH, "oct8_pools.json")))
    copies = [p for p in D["pools"] if p["kind"] == "copy"]
    data = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
    data["copies"] = copies; data["first"] = D["first"]; data["last"] = D["last"]
    if "head" not in data:
        data["head"] = int(rpc("eth_blockNumber", []), 16)
    head = data["head"]
    if "code" not in data:
        data["code"] = batch([("eth_getCode", [p["to"], hex(p["block"])]) for p in copies])
        data["code_prev"] = batch([("eth_getCode", [p["to"], hex(p["block"] - 1)]) for p in copies])
        pickle.dump(data, open(CACHE, "wb")); print("code done", file=sys.stderr)
    if "rec" not in data:
        data["rec"] = batch([("eth_getTransactionReceipt", [p["tx"]]) for p in copies])
        pickle.dump(data, open(CACHE, "wb")); print("receipts done", file=sys.stderr)
    data.setdefault("blocks", {}); data.setdefault("logs", {})
    for i, p in enumerate(copies):
        pid = p["pid"]; b0 = p["block"]
        if pid not in data["blocks"]:
            data["blocks"][pid] = batch([("eth_getBlockByNumber", [hex(b0 + k), True]) for k in range(SCAN)])
        if pid not in data["logs"]:
            data["logs"][pid] = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + LOG_SPAN, head))
        if (i + 1) % 5 == 0:
            pickle.dump(data, open(CACHE, "wb"))
        print(f"  {i + 1}/{len(copies)} {b0}: {len(data['logs'][pid])} logs", file=sys.stderr)
    pickle.dump(data, open(CACHE, "wb"))
    # transactions behind every swap/ML in L..L+SCAN that is not already in the fetched blocks (none should be missing)
    if "relay_logs" not in data:
        data["relay_logs"] = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, D["first"], min(D["last"] + 20000, head))
        data["relay_receipts"] = batch([("eth_getTransactionReceipt", [l["transactionHash"]]) for l in data["relay_logs"]])
        hs = sorted({l["transactionHash"] for l in data["relay_logs"]})
        data["relay_txs"] = dict(zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs])))
        pickle.dump(data, open(CACHE, "wb")); print(f"relay swaps on the day: {len(data['relay_logs'])}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
