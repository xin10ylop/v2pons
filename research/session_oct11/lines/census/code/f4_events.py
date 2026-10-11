#!/usr/bin/env python3
"""Stage 4: every pool's events over [launch, launch + 3000] (capped at the head at fetch time).
v4: PoolManager Swap + ModifyLiquidity by pool id (topic 1 list); V2: Swap/Mint/Burn by pair address list; V3: Swap/Mint/Burn by pool list.
Groups: <= GMAX pools of one kind whose launches lie within 6,000 blocks; range [first launch, last launch + 3000].
The first census's raw v4 ETH events (its 48 h window) are reused (parsed) instead of refetched.
Output cache/ev.jsonl: one row per group {kind, ids, launch{id: bn}, a, b, head, ev: [compact events]}."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *
GMAX = 50


def compact(kind, l):
    t = l["topics"]; d = l["data"]; bn = int(l["blockNumber"], 16) if isinstance(l.get("blockNumber"), str) else l["bn"]
    ti = int(l["transactionIndex"], 16) if isinstance(l.get("transactionIndex"), str) else l["ti"]
    li = int(l["logIndex"], 16) if isinstance(l.get("logIndex"), str) else l["li"]
    tx = l.get("transactionHash") or l["tx"]; addr = (l.get("address") or l.get("addr")).lower()
    if kind == "v4":
        pid = t[1]; snd = A(t[2])
        if t[0] == T_SWAP: return ["s", bn, ti, li, pid, snd, sgn(W(d, 0)), sgn(W(d, 1)), W(d, 2), W(d, 3), sgn(W(d, 4)), W(d, 5), tx]
        if t[0] == T_ML: return ["m", bn, ti, li, pid, snd, sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), d[2 + 64 * 3: 2 + 64 * 4], tx]
    elif kind == "v2":
        if t[0] == T2_SWAP: return ["s", bn, ti, li, addr, A(t[1]), W(d, 0), W(d, 1), W(d, 2), W(d, 3), A(t[2]), tx]
        if t[0] == T2_MINT: return ["mi", bn, ti, li, addr, A(t[1]), W(d, 0), W(d, 1), tx]
        if t[0] == T2_BURN: return ["b", bn, ti, li, addr, A(t[1]), W(d, 0), W(d, 1), A(t[2]), tx]
    else:
        if t[0] == T3_SWAP: return ["s", bn, ti, li, addr, A(t[1]), A(t[2]), sgn(W(d, 0)), sgn(W(d, 1)), W(d, 2), W(d, 3), sgn(W(d, 4)), tx]
        if t[0] == T3_MINT: return ["mi", bn, ti, li, addr, A(t[1]), sgn(int(t[2], 16)), sgn(int(t[3], 16)), W(d, 1), W(d, 2), W(d, 3), tx]
        if t[0] == T3_BURN: return ["b", bn, ti, li, addr, A(t[1]), sgn(int(t[2], 16)), sgn(int(t[3], 16)), W(d, 0), W(d, 1), W(d, 2), tx]
    return None


def kind_of(p): return "v4" if p["dex"] == "v4" else "v3" if p["dex"] == "v3" else "v2"


def seed_old():
    """parse the first census's ev_groups (v4 ETH pools, windows complete) into ev.jsonl once"""
    if jget("seeded_old_events.json"): return
    t0 = time.time(); n = 0
    for g in jl_iter("ev_groups.jsonl", OLD):
        ev = [compact("v4", l) for l in g["logs"]]
        jl_append("ev.jsonl", [{"kind": "v4", "ids": g["pids"], "launch": g["launch"], "a": g["a"], "b": g["b"], "head": g["head"], "old": True,
                                "ev": [e for e in ev if e]}]); n += 1
    jput("seeded_old_events.json", {"groups": n, "secs": round(time.time() - t0)}); log("seeded old groups", n)


if __name__ == "__main__":
    t0 = time.time()
    seed_old()
    P = [p for p in base_pools()]
    done = set()
    for g in jl_iter("ev.jsonl"):
        for i in g["ids"]: done.add(i)
    head = int(rpc("eth_blockNumber", []), 16)
    todo = [p for p in P if p["pool"] not in done and p["launch_block"] + 50 <= head]
    groups = []
    for kind in ("v4", "v2", "v3"):
        g = []
        for p in sorted([p for p in todo if kind_of(p) == kind], key=lambda p: p["launch_block"]):
            if g and (p["launch_block"] - g[0]["launch_block"] > 6000 or len(g) >= GMAX): groups.append((kind, g)); g = []
            g.append(p)
        if g: groups.append((kind, g))
    groups.sort(key=lambda kg: kg[1][0]["launch_block"])
    log("events todo pools", len(todo), "groups", len(groups), collections.Counter(k for k, _ in groups), "head", head)
    for gi, (kind, g) in enumerate(groups):
        a = g[0]["launch_block"]; z = min(head, g[-1]["launch_block"] + SPAN); ids = [p["pool"] for p in g]
        if kind == "v4": flt = {"address": PM, "topics": [[T_SWAP, T_ML], ids]}
        elif kind == "v2": flt = {"address": ids, "topics": [[T2_SWAP, T2_MINT, T2_BURN]]}
        else: flt = {"address": ids, "topics": [[T3_SWAP, T3_MINT, T3_BURN]]}
        ls = logs(flt, a, z)
        ev = [compact(kind, l) for l in ls]
        jl_append("ev.jsonl", [{"kind": kind, "ids": ids, "launch": {p["pool"]: p["launch_block"] for p in g}, "a": a, "b": z, "head": head, "ev": [e for e in ev if e]}])
        if gi % 50 == 0: log("events", gi, "/", len(groups), kind, len(ls), f"{time.time() - t0:.0f}s", STATS)
    timing("f4_events", time.time() - t0, {"pools": len(todo), "groups": len(groups)})
    log("STATS", STATS)
