#!/usr/bin/env python3
"""Stage 5: transactions of every pull in the window, of the first 12 swaps of every pool, and of the buys in the 200 blocks before each
first pull (and before the first full pull when that is another one) that are not among the first 12 swaps (the 12 closest to the
pull, 6 for the full pull), and of the first real buy (>= 0.005 ETH-equivalent) when it is not among the first 12 swaps. Reuses the first census's cached txs. Output cache/tx_swap.jsonl."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evload import *
NFIRST, PRE_WIN, PRE_CAP = 12, 200, 12

if __name__ == "__main__":
    t0 = time.time()
    P = {p["pool"]: p for p in base_pools()}
    LB_MIN = int(os.environ.get("LB_MIN", "0")); OUT = os.environ.get("OUT", "tx_swap.jsonl")
    keep = None
    if LB_MIN:
        old = set()
        for g in jl_iter("ev_groups.jsonl", OLD): old.update(g["pids"])
        keep = {i for i, p in P.items() if p["launch_block"] >= LB_MIN and i not in old}
    EV = load_events(keep)
    pulls_h, first_h, pre_h = [], [], []
    for i, o in EV.items():
        p = P.get(i)
        if not p: continue
        sw, adds, pulls = norm(p, o)
        pulls_h += [x["tx"] for x in pulls]
        first_h += [x["tx"] for x in sw[:NFIRST]]
        f = (1 if p["quote"] in ("ETH", "WETH") else ETH_PER_USDG) / 10 ** (18 if p["quote"] != "USDG" else 6)
        frb = [x for x in sw if x["buy"] and x["q"] * f >= 0.005]
        if frb and sw.index(frb[0]) >= NFIRST: pre_h.append(frb[0]["tx"])
        if pulls:
            pl = pulls[0]
            ex = [x["tx"] for x in sw[NFIRST:] if x["buy"] and pl["bn"] - PRE_WIN <= x["bn"] <= pl["bn"] and (x["bn"], x["li"]) < (pl["bn"], pl["li"])]
            pre_h += list(dict.fromkeys(ex))[-PRE_CAP:]
    have = {x["hash"] for x in jl_iter("tx_launch.jsonl")} | {x["hash"] for x in jl_iter("tx_swap.jsonl")} | {x["hash"] for x in jl_iter("tx_swap_b.jsonl")}
    want = (set(pulls_h) | set(first_h) | set(pre_h)) - have
    seed = []
    for x in jl_iter("stx.jsonl", OLD):
        if x["hash"] in want:
            y = {k: v for k, v in x.items() if k not in ("input512", "input", "auth")}
            y["input_head"] = (x.get("input") or x.get("input512"))[:10 + 64 * 6]
            if x.get("auth"): y["auth"] = len(x["auth"])
            seed.append(y); want.discard(x["hash"]); have.add(x["hash"])
    jl_append(OUT, seed)
    log("pools", len(EV), "pull txs", len(set(pulls_h)), "first-12 txs", len(set(first_h)), "pre-pull txs", len(set(pre_h)), "seeded", len(seed), "to fetch", len(want))
    order = list(dict.fromkeys(pulls_h + first_h + pre_h))
    fetch_txs(order, OUT, "stx", head_words=6, have=have, chunk=1000)
    timing("f5_stx", time.time() - t0, {"pull": len(set(pulls_h)), "first": len(set(first_h)), "pre": len(set(pre_h))})
    log("STATS", STATS)
