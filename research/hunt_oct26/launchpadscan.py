#!/usr/bin/env python3
"""launchpadscan.py HOURS: every no-hook, native v4 pool launched at the launchpad's standard price (sqrtPriceX96 2505036234966386302045715536678303),
any fee and tick spacing; per (fee, tick spacing): launches a day and watchfee0's ride (with the pool's fee), buy ENTRY_LAG and sell LAG late."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24; SP = 2505036234966386302045715536678303
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
init = W.getlogs(head - int(HOURS * 36000), head - W.WIN - 2, [W.T_INIT4], W.PM)
grp = collections.defaultdict(list); allsp = 0
for l in init:
    d = l["data"][2:]
    if l["topics"][2] != "0x" + "0" * 64 or int(d[128 + 24:192], 16) != 0:
        continue
    if int(d[192:256], 16) != SP:
        continue
    allsp += 1
    grp[(int(d[0:64], 16), H.i256(d[64:128]))].append((l["topics"][1], int(l["blockNumber"], 16)))
print(f"last {HOURS:g} h: {allsp} no-hook native pools at the launchpad price; by (fee ppm, tick spacing):", {k: len(v) for k, v in grp.items()}, flush=True)
for (fee, ts), ps in sorted(grp.items(), key=lambda kv: -len(kv[1])):
    rs = []; none = 0
    for pid, bn in ps:
        try:
            r = W.ride(pid, bn, fee)
        except RuntimeError:
            continue
        if r is None:
            none += 1
        else:
            rs.append(r)
    if rs:
        rr = [r["ret"] for r in rs]
        print(f"  fee {fee/1e4:g}% ts {ts}: {len(ps)} pools ({len(ps)/(HOURS/24):.0f}/day); no crowd buy: {none}; rides {len(rs)}: mean {st.mean(rr):+.1%}, median {st.median(rr):+.1%}, won {sum(x>0 for x in rr)}/{len(rr)}, pulled first {sum(1 for r in rs if r['why']=='pull')}", flush=True)
    else:
        print(f"  fee {fee/1e4:g}% ts {ts}: {len(ps)} pools ({len(ps)/(HOURS/24):.0f}/day); no rides (no crowd buy in {none})", flush=True)
