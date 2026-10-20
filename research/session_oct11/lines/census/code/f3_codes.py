#!/usr/bin/env python3
"""Stage 3: code hashes (exact, mask32, skeleton, size) at latest for every token and every launch target / created contract."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *
from evmhash import code_hashes

if __name__ == "__main__":
    t0 = time.time()
    P = base_pools()
    addrs = {p["token"] for p in P}
    for t in jl_iter("tx_launch.jsonl"):
        if t.get("to"): addrs.add(t["to"])
    for r in jl_iter("rcpt.jsonl"):
        if r.get("contract"): addrs.add(r["contract"])
    have = {x["addr"] for x in jl_iter("codes.jsonl")}
    need = sorted(a for a in addrs if a not in have and a != Z)
    log("codes need", len(need), "have", len(have))
    for i in range(0, len(need), 500):
        ch = need[i:i + 500]; r = code_hashes(ch, per_call=25)
        jl_append("codes.jsonl", [{"addr": a, **(v or {"err": True})} for a, v in r.items()])
        if (i // 500) % 10 == 0: log("codes", i + len(ch), "/", len(need), STATS)
    timing("f3_codes", time.time() - t0, {"addresses": len(need)})
    log("STATS", STATS)
