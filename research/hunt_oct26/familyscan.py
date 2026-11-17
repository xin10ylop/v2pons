#!/usr/bin/env python3
"""familyscan.py HOURS: every no-hook, native v4 pool launched on Robinhood in the last HOURS, grouped into launch families by (fee, tick
spacing, launch sqrtPriceX96); for each family with MIN_POOLS+ pools: launches a day and watchfee0's ride (buy behind the first crowd buy of
TRIG_ETH+, sell at take-profit TP or the cap, the pool's fee, -100% on a pull) with the buy ENTRY_LAG and the sell LAG blocks late. A
positive family is a candidate only: the ride cannot see a line that pulls or burns on an outsider's buy, so each needs the reaction and
exit tests. Read-only."""
import os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24; MIN_POOLS = int(os.environ.get("MIN_POOLS", "15"))
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
init = W.getlogs(head - int(HOURS * 36000), head - W.WIN - 2, [W.T_INIT4], W.PM)
fam = collections.defaultdict(list); n_native = 0
for l in init:
    d = l["data"][2:]
    if l["topics"][2] != "0x" + "0" * 64 or int(d[128 + 24:192], 16) != 0:
        continue
    n_native += 1
    fam[(int(d[0:64], 16), H.i256(d[64:128]), int(d[192:256], 16))].append((l["topics"][1], int(l["blockNumber"], 16)))
big = {k: v for k, v in fam.items() if len(v) >= MIN_POOLS}
print(f"last {HOURS:g} h: {n_native} no-hook native v4 pools in {len(fam)} launch families; {len(big)} with {MIN_POOLS}+ pools", flush=True)
for (fee, ts, sp), ps in sorted(big.items(), key=lambda kv: -len(kv[1])):
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
    head_s = f"fee {fee/1e4:g}% ts {ts} sqrtP {str(sp)[:12]}..: {len(ps)} pools ({len(ps)/(HOURS/24):.0f}/day); no crowd buy {none}"
    if rs:
        rr = [r["ret"] for r in rs]
        print(f"  {head_s}; rides {len(rs)}: mean {st.mean(rr):+.1%}, median {st.median(rr):+.1%}, won {sum(x>0 for x in rr)}/{len(rr)}, pulled first {sum(1 for r in rs if r['why']=='pull')}, held to cap {sum(1 for r in rs if r['why']=='hold')}", flush=True)
    else:
        print(f"  {head_s}; no rides", flush=True)
