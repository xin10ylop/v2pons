#!/usr/bin/env python3
"""rivals_timeline.py: when was each front-runner wallet of rivals_now.py active? Its nonce at fixed look-backs (archive state) on Base and
BNB, and on Robinhood as far back as its public node keeps state. A rise between two look-backs = transactions sent in that interval.
Read-only, public RPCs."""
import sys, concurrent.futures as cf
from rivals_now import rpc, W

EP = {"base": "https://base.drpc.org", "bsc": "https://bsc-mainnet.public.blastapi.io", "rh": "https://rpc.mainnet.chain.robinhood.com"}
BPD = {"base": 43200, "bsc": 192000, "rh": 864000}            # blocks a day (Base 2 s; BNB 0.45 s; Robinhood ~0.1 s)
DAYS = [0, 1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60, 90]
WAL = [k for k in W if not k.startswith("router")]


def nonce_at(ch, a, blk):
    r = rpc(EP[ch], "eth_getTransactionCount", [a, hex(blk)], tries=3)
    return int(r, 16) if isinstance(r, str) and r.startswith("0x") else None


if __name__ == "__main__":
    chains = sys.argv[1:] or ["base", "bsc", "rh"]
    for ch in chains:
        head = int(rpc(EP[ch], "eth_blockNumber", []), 16)
        jobs = [(k, d) for k in WAL for d in DAYS]
        with cf.ThreadPoolExecutor(8) as ex:
            got = dict(zip(jobs, ex.map(lambda t: nonce_at(ch, W[t[0]], head - t[1] * BPD[ch]), jobs)))
        print(f"\n== {ch} (head {head}); nonce at N days ago: " + " ".join(f"{d:>6}" for d in DAYS))
        for k in WAL:
            row = [got[(k, d)] for d in DAYS]
            if all(v in (0, None) for v in row):
                continue
            print(f"{k:16}" + "".join(f"{'-' if v is None else v:>7}" for v in row))
