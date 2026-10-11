"""Loaders for the scanner2 census (json only; big ints stay exact). Usage:
    import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census")
    from load import *
    P = load_pools()                 # pool -> row (pools.jsonl)
    F = load_families("tok")         # list of family summaries (tok | tokm | lc | strict | fund | fund1), each with "pools"
    E = load_events(pool_ids)        # raw per-pool events (cache/ev.jsonl, compact rows; see README "events")
    T = load_txs()                   # tx hash -> trimmed transaction (launch + swap/pull caches)
"""
import os, sys, json
CEN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(CEN, "code"))


def load_pools():
    out = {}
    with open(os.path.join(CEN, "pools.jsonl")) as f:
        for line in f:
            r = json.loads(line); out[r["pool"]] = r
    return out


def load_families(grouping="tok"): return json.load(open(os.path.join(CEN, f"families_{grouping}.json")))
def load_summary(): return json.load(open(os.path.join(CEN, "summary.json")))
def load_top40(): return json.load(open(os.path.join(CEN, "top40.json")))


def load_events(keep=None):
    from evload import load_events as le
    return le(set(keep) if keep is not None else None)


def load_txs():
    out = {}
    for n in ("tx_launch.jsonl", "tx_swap.jsonl", "tx_swap_b.jsonl"):
        p = os.path.join(CEN, "cache", n)
        if not os.path.exists(p): continue
        with open(p) as f:
            for line in f:
                try: x = json.loads(line); out[x["hash"]] = x
                except Exception: pass
    return out
