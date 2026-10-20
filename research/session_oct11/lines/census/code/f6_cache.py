#!/usr/bin/env python3
"""Stage 6b (no RPC): the same funding scan for every other launch wallet (launch nonce <= 3) whose blocks back from its launch are already in
the block cache of stage 6 (contiguously, down to its funding). Output cache/funding_cache.jsonl (same rows as funding.jsonl, plus
"from_cache": true); only wallets whose funding is found inside the contiguous cached blocks are kept."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6_funding as F
from base import *


def get_blocks_cached(bns):
    miss = [b for b in bns if b not in F.BL]
    if miss: raise KeyError(min(miss))


if __name__ == "__main__":
    t0 = time.time(); F.load_blocks(); log("blocks", len(F.BL))
    F.get_blocks = get_blocks_cached
    done = {x["wallet"] for x in jl_iter("funding.jsonl")} | {x["wallet"] for x in jl_iter("funding_cache.jsonl")}
    rows = sorted(F.families(), key=lambda r: r["lb"]); n = 0; gaps = 0
    out = []
    for r in rows:
        if r["nonce"] > F.NONCE_MAX or r["wallet"] in done: continue
        d = 0
        while d < 800 and (r["lb"] - d) in F.BL: d += 1
        if d < 40: continue
        F.MAXBACK = d
        res = F.scan(r["wallet"], r["lb"], r["ti"], r["nonce"])
        if res["status"] != "found": gaps += 1; continue
        res.update({"pool": r["pool"], "tok": r["tok"], "lk": r["lk"], "from_cache": True}); out.append(res); done.add(r["wallet"]); n += 1
    jl_append("funding_cache.jsonl", out)
    log("cache-resolved", n, "gaps", gaps, collections.Counter(x["status"] for x in out), f"{time.time() - t0:.0f}s")
