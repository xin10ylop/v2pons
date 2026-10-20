#!/usr/bin/env python3
"""The fresh-wallet buyer router 0x27fad47c (selector 0f4f745a) seen in 3 pools of the POSM1444 fee-0.3% family: where else does it buy
(every pool in the census), its offsets, sizes, wallets; and the front rule priced on those pools at several stakes (sell one block after
the last buy of its burst, or after its first buy)."""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ana import *   # noqa
R27 = "0x27fad47c0abef79bfe44830f170ec0724ded5d12"
P = load_pools(); T = load_txs(); M = load_blocks_meta()
txs27 = [t for t in T.values() if t["to"] == R27]
pids = sorted({ref[0] for t in txs27 for ref in t["refs"]})
print("txs to 0x27fad47c in the census:", len(txs27), "pools", len(pids), "selectors", collections.Counter(t["selector"] for t in txs27),
      "from nonces", collections.Counter(t["nonce"] for t in txs27).most_common(4), "values", collections.Counter(t["value_eth"] for t in txs27).most_common(4))
print("families:", collections.Counter(P[p]["family"] for p in pids).most_common(10))
E = load_events(set(pids))
out = {"n_txs": len(txs27), "pools": []}
for pid in pids:
    p = P[pid]; pl = Pool(p, E.get(pid), T, M)
    b = [x for x in pl.seq if x["buy"] and x["eth"] < 2 * 10**14 and x["sender"] == R27] or [x for x in pl.seq if x["to"] == R27]
    offs = [x["bn"] - pl.b0 for x in b]
    depth_eth = pl.L0 * Q96 / pl.s_eff / 1e18 if pl.L0 else 0
    row = {"pid": pid, "family": p["family"], "deployer": p["launch_from"], "nonce": p["launch_nonce"], "value": p["launch_value_eth"], "L0": pl.L0,
           "eth_depth_L_over_sqrtP": round(depth_eth, 6), "n27": len(b), "offs": [min(offs), max(offs)] if offs else None, "eth27": sum(x["eth"] for x in b) / 1e18,
           "pull": (pl.pull_bn - pl.b0) if pl.pull_bn else None, "n_swaps": len(pl.seq)}
    if b:
        last = max(x["bn"] for x in b); first = min(x["bn"] for x in b)
        row["front"] = {}
        for stake in (10**13, 5 * 10**13, 10**14, 5 * 10**14, STAKE):
            t1 = pl.trade(pl.b0 + 1, last + 1, stake=stake); t2 = pl.trade(pl.b0 + 1, first + 1, stake=stake)
            row["front"][stake / 1e18] = {"sell_after_burst": t1.get("ret") and round(t1["ret"], 4), "gross": t1.get("gross") and round(t1["gross"], 4),
                                          "usd": t1.get("ret") and round(t1["ret"] * stake / 1e18 * USD_PER_ETH, 5),
                                          "sell_after_first": t2.get("ret") and round(t2["ret"], 4)}
    out["pools"].append(row); print(json.dumps(row))
json.dump(out, open(os.path.join(HERE, "router27.json"), "w"), indent=1)
