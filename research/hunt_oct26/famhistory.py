#!/usr/bin/env python3
"""famhistory.py FEE TS SQRTP [MAX_DAYS]: launches per day of one v4 launch family (fee, tick spacing, launch sqrtPriceX96, no hook, native),
going back day by day from now until 5 empty days in a row (or MAX_DAYS). Read-only."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
FEE, TS, SP = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); MAXD = int(sys.argv[4]) if len(sys.argv) > 4 else 45
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16); DAY = 864000
empty = 0; total = 0; first = None
for d in range(MAXD):
    hi = head - d * DAY; lo = hi - DAY + 1
    n = 0
    for l in W.getlogs(lo, hi, [W.T_INIT4], W.PM):
        x = l["data"][2:]
        if (l["topics"][2] == "0x" + "0" * 64 and int(x[128 + 24:192], 16) == 0 and int(x[0:64], 16) == FEE and H.i256(x[64:128]) == TS
                and int(x[192:256], 16) == SP):
            n += 1; first = int(l["blockNumber"], 16) if first is None or int(l["blockNumber"], 16) < first else first
    t = H.ts(url, hi)
    print(f"day ending {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t))} UTC: {n} launches", flush=True)
    total += n; empty = empty + 1 if n == 0 else 0
    if empty >= 5:
        break
if first:
    print(f"total {total}; first launch seen at block {first} ({time.strftime('%Y-%m-%d %H:%M', time.gmtime(H.ts(url, first)))} UTC)")
