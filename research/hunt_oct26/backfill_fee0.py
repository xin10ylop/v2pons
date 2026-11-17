#!/usr/bin/env python3
"""backfill_fee0.py HOURS: watchfee0's dry-run rules replayed over the last HOURS of recorded Robinhood blocks (every fee-0, no-hook, native
v4 pool launched in the window, scored with watchfee0.ride once its follow window has closed). Read-only."""
import os, sys, time, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H
import watchfee0 as W
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
url = H.CH["rh"]["rpc"]; head = int(H.rpc(url, "eth_blockNumber", []), 16)
lo = head - int(HOURS * 36000); hi = head - W.WIN - 2
pools = []
for l in W.getlogs(lo, hi, [W.T_INIT4], W.PM):
    d = l["data"][2:]
    if int(d[0:64], 16) == 0 and int(d[128 + 24:192], 16) == 0 and l["topics"][2] == "0x" + "0" * 64:
        pools.append((l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"]))
print(f"last {HOURS:g} h (blocks {lo}..{hi}): {len(pools)} fee-0, no-hook, native pools", flush=True)
txs = H.batch(url, [("eth_getTransactionByHash", [t]) for _, _, t in pools], size=50, workers=4, tries=8) if pools else []
launcher = collections.Counter((x.get("to") or "")[:10] if x else "?" for x in txs)
print("launch targets:", launcher.most_common(8), flush=True)
res = []; none = 0
for (pid, bn, tx), x in zip(pools, txs):
    try:
        r = W.ride(pid, bn)
    except RuntimeError as e:
        print(f"  {pid[:14]} read error {str(e)[:60]}"); continue
    if r is None:
        none += 1; continue
    r["to"] = (x.get("to") or "")[:10] if x else "?"; res.append(r)
    print(f"  {pid[:14]} via {r['to']}: demand {r['trig_eth']:.3f} via {r['trig_who']} at +{r['trig_off']}, exit +{r['exit_off']} ({r['why']}), pull {r['pull']} -> {r['ret']:+.1%}", flush=True)
print(f"\npools with no demand buy >= {W.TRIG_ETH} ETH: {none}")
if res:
    rr = [r["ret"] for r in res]
    print(f"scored rides: {len(res)}; mean {st.mean(rr):+.1%}, median {st.median(rr):+.1%}, won {sum(x > 0 for x in rr)}/{len(rr)}, "
          f"take-profit {sum(1 for r in res if r['why'] == 'take-profit')}, pulled first {sum(1 for r in res if r['why'] == 'pull')}, held to cap {sum(1 for r in res if r['why'] == 'hold')}")
    by = collections.defaultdict(list)
    for r in res:
        by[r["to"]].append(r["ret"])
    for t, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"  launch target {t}: {len(v)} rides, mean {st.mean(v):+.1%}, won {sum(x > 0 for x in v)}/{len(v)}")
