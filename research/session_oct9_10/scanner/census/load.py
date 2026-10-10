"""Loader for the Robinhood Chain v4 ETH-pool census (see README.md for every field).

    import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
    from load import *
    P = load_pools()        # pid -> pool row
    E = load_events()       # pid -> {swaps, pulls, adds, zero_mods, ev_from, ev_to, complete}
    T = load_txs()          # tx hash -> tx row (launch / first-8-swap / first-2-pull transactions)
    F = load_families()     # family key -> family row (pids, values_eth, known, ...)
    B = load_blocks()       # launch block (int) -> unix timestamp

Only json is used; integers (sqrt prices, liquidity, wei amounts, signed amounts) are exact Python ints.
"""
import json, os

DIR = os.path.dirname(os.path.abspath(__file__))


def _jsonl(name, key):
    out = {}
    with open(os.path.join(DIR, name)) as f:
        for line in f:
            r = json.loads(line); out[r[key]] = r
    return out


def load_pools():
    """pid -> pool row (pools.jsonl): every ETH-paired (currency0 = 0x0) v4 pool initialized in the window"""
    return _jsonl("pools.jsonl", "pid")


def load_events(pids=None):
    """pid -> events row (events.jsonl). pids: an optional set to keep (the file is large; filtering while reading saves memory)"""
    if pids is None: return _jsonl("events.jsonl", "pid")
    pids = set(pids); out = {}
    with open(os.path.join(DIR, "events.jsonl")) as f:
        for line in f:
            if line.startswith('{"pid":"'):                                # fast path: every row is written with pid first
                if line[8:74] not in pids: continue
            r = json.loads(line)
            if r["pid"] in pids: out[r["pid"]] = r
    return out


def load_txs():
    """tx hash -> transaction row (txs.jsonl)"""
    return _jsonl("txs.jsonl", "hash")


def load_families():
    """family key -> family row (families.json); key = launch_to|selector|calldata_len|fee|tick_spacing|hooks_zero(true/false)"""
    return json.load(open(os.path.join(DIR, "families.json")))


def load_blocks():
    """launch block number (int) -> unix timestamp (int)"""
    return {int(k): v for k, v in json.load(open(os.path.join(DIR, "blocks.json"))).items()}


def load_blocks_meta():
    """launch block number (int) -> (timestamp, baseFeePerGas wei, tx count)"""
    return {int(k): tuple(v) for k, v in json.load(open(os.path.join(DIR, "blocks_meta.json"))).items()}


def load_loose_families():
    """selector|calldata_len|fee|tick_spacing|hooks_zero -> {count, n_launch_to, top_launch_to, code_hashes} (operators with many launch contracts)"""
    return json.load(open(os.path.join(DIR, "loose_families.json")))


def load_code_families():
    """code_hash|selector|calldata_len|fee|tick_spacing|hooks_zero -> group (launch contracts with identical code, e.g. one contract per launch)"""
    return json.load(open(os.path.join(DIR, "code_families.json")))


def load_to_families():
    """launch_to|selector|calldata_len -> group across fee tiers (launchers that vary the fee per launch: operator A, the 54,500-byte POSM batches)"""
    return json.load(open(os.path.join(DIR, "to_families.json")))


def load_other_v4():
    """pid -> non-ETH v4 pool (currency0 != 0: USDG, WETH, ...) initialized in the window; Initialize fields only, no events"""
    return _jsonl("v4_other_pools.jsonl", "pid")


def load_dex():
    """(other_dex.json summary, [dex_pairs.jsonl rows], [bonding_creates.jsonl rows])"""
    s = json.load(open(os.path.join(DIR, "other_dex.json")))
    pairs = [json.loads(l) for l in open(os.path.join(DIR, "dex_pairs.jsonl"))]
    fac = [json.loads(l) for l in open(os.path.join(DIR, "bonding_creates.jsonl"))]
    return s, pairs, fac


def is_buy(swap):
    """a0 < 0: ETH went into the pool (currency0 = ETH), the swapper bought the token"""
    return swap["a0"] < 0


__all__ = ["load_pools", "load_events", "load_txs", "load_families", "load_blocks", "load_blocks_meta", "load_loose_families", "load_code_families", "load_to_families",
           "load_other_v4", "load_dex", "is_buy", "DIR"]
