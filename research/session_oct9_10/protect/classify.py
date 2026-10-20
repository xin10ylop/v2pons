"""Shared classification: crowd = the operator crowd's transaction fingerprint (UR execute, 1124 bytes, deadline 2^256-1, type 2,
priority 0.02 gwei, gas limit 220000/880000/260000); us = our relay / wallet; dust = the dust tester; outsider = anything else."""
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load import *


def crowd_fp(x):
    f = x["fp"] or {}
    return f.get("type") == 2 and f.get("prio") == 20_000_000 and f.get("len") == 1124 and f.get("dl_max") is True and f.get("gas") in (220_000, 880_000, 260_000)


def cls(x, crowd_wallets=None):
    if is_us(x): return "us"
    if x["from"] == DUST: return "dust"
    if x["from"] is None: return "?"
    if x["a0"] < 0: return "crowd" if crowd_fp(x) else "outsider"
    return "crowd" if (crowd_wallets and x["from"] in crowd_wallets) else "outsider"


def annotate(pools):
    cw = {x["from"] for p in pools for x in p["sw"] if x["a0"] < 0 and not is_us(x) and crowd_fp(x)}
    for p in pools:
        for x in p["sw"]: x["cls"] = cls(x, cw)
    return cw


def mean_block_ms(b_lo, b_hi, cache={}):
    """mean block time (ms) over [b_lo, b_hi] from the block timestamps (seconds)"""
    from chain import rpc
    k = (b_lo, b_hi)
    if k not in cache:
        t = [int(rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16) for b in (b_lo, b_hi)]
        cache[k] = 1000 * (t[1] - t[0]) / (b_hi - b_lo)
    return cache[k]
