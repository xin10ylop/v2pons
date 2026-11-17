#!/usr/bin/env python3
"""stakesweep.py HOURS: the fee-0 launch family's ride at several stakes, on the same pools (each pool's logs fetched once), with the
buy landing ENTRY_LAG and the sell LAG blocks late. Prints mean / median / won, the share that reached take-profit, and ETH a day."""
import os, sys, statistics as st, functools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
W.getlogs = functools.lru_cache(maxsize=None)(lambda lo, hi, topics, address=None: _gl(lo, hi, topics, address))
_raw = W.getlogs.__wrapped__ if hasattr(W.getlogs, "__wrapped__") else None
def _gl(lo, hi, topics, address):
    out = []
    for a in range(lo, hi + 1, 30000):
        q = {"fromBlock": hex(a), "toBlock": hex(min(hi, a + 29999)), "topics": [list(t) if isinstance(t, tuple) else t for t in topics]}
        if address: q["address"] = address
        out += H.rpc(W.url, "eth_getLogs", [q]) or []
    return out
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int(HOURS * 36000); hi = head - W.WIN - 2
init = W.getlogs(lo, hi, (W.T_INIT4,), W.PM)
pools = [(l["topics"][1], int(l["blockNumber"], 16)) for l in init if int(l["data"][2:][0:64], 16) == 0 and int(l["data"][2:][64:128], 16) == 60
         and int(l["data"][2:][128 + 24:192], 16) == 0 and l["topics"][2] == "0x" + "0" * 64]
print(f"last {HOURS:g} h: {len(pools)} pools (fee 0, tick spacing 60, no hook); buy lands {W.ENTRY_LAG} late, sell {W.LAG} late, take-profit {W.TP:.0%}, cap {W.HOLD}", flush=True)
# ride() calls getlogs with list topics; make them hashable
_orig_ride = W.ride
def ride_cached(pid, bn):
    gl = W.getlogs
    W.getlogs = lambda lo, hi, topics, address=None: gl(lo, hi, tuple(tuple(t) if isinstance(t, list) else t for t in topics), address)
    try:
        return _orig_ride(pid, bn)
    finally:
        W.getlogs = gl
days = HOURS / 24
print(f"{'stake ETH':>9s} {'~USD':>6s} | {'mean':>7s} {'median':>7s} {'won':>6s} {'TP hit':>6s} {'held to cap':>11s} | {'ETH/day':>8s}")
for stake in (0.0017, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5):
    W.STAKE = int(stake * 1e18)
    rs = [r for r in (ride_cached(pid, bn) for pid, bn in pools) if r]
    if not rs: continue
    rr = [r["ret"] for r in rs]
    print(f"{stake:9.4f} {stake*3000:6.0f} | {st.mean(rr):+7.1%} {st.median(rr):+7.1%} {sum(x>0 for x in rr):3d}/{len(rr):<2d} {sum(1 for r in rs if r['why']=='take-profit'):6d} {sum(1 for r in rs if r['why']=='hold'):11d} | {st.mean(rr)*stake*len(rr)/days:+8.4f}", flush=True)
