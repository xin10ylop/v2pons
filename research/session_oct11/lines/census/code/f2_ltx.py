#!/usr/bin/env python3
"""Stage 2: launch transactions (eth_getTransactionByHash), creation receipts. Reuses the first census's cached txs."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *

if __name__ == "__main__":
    t0 = time.time()
    P = base_pools(); log("pools", len(P), collections.Counter(p["dex"] for p in P))
    hs = list(dict.fromkeys(p["launch_tx"] for p in P))
    have = {x["hash"] for x in jl_iter("tx_launch.jsonl")}
    # seed from the first census (launch txs there have the full input below 2,048 bytes; input512 otherwise)
    seed = []
    want = set(hs) - have
    for x in old_tx_iter():
        if x["hash"] in want:
            y = {k: v for k, v in x.items() if k not in ("input512", "auth")}
            if "input" not in y: y["input_head"] = x.get("input512")
            if x.get("auth"): y["auth"] = len(x["auth"])
            seed.append(y); want.discard(x["hash"]); have.add(x["hash"])
    jl_append("tx_launch.jsonl", seed); log("seeded from first census", len(seed))
    fetch_txs(hs, "tx_launch.jsonl", "ltx", have=have)
    T = {x["hash"]: x for x in jl_iter("tx_launch.jsonl")}
    hr = {x["hash"] for x in jl_iter("rcpt.jsonl")}
    need = [h for h, t in T.items() if t["to"] is None and h not in hr]
    log("creation receipts", len(need))
    for i in range(0, len(need), 25):
        ch = need[i:i + 25]; r = batch([("eth_getTransactionReceipt", [h]) for h in ch], size=25)
        jl_append("rcpt.jsonl", [{"hash": h, "contract": (x.get("contractAddress") or "").lower() or None, "status": x.get("status"), "gas_used": int(x["gasUsed"], 16)} for h, x in zip(ch, r) if x])
    timing("f2_ltx", time.time() - t0, {"launch_txs": len(hs)})
    log("STATS", STATS)
