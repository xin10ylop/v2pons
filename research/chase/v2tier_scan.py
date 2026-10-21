#!/usr/bin/env python3
"""v2tier_scan.py RPC FACTORY WETH ROUTER LO HI DAYS OUT [HORIZON]: one tier of a V2 pump-and-pull line: the WETH pairs created in the last DAYS
whose creation is a fresh wallet's nonce-2 addLiquidityETH on ROUTER with LO <= msg.value <= HI ETH; their Mint, Burn and Swap logs inside
HORIZON blocks, and the transaction behind every swap (no cap), for the reaction and the seat (Robinhood: 10 blocks a second)."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from v2scan import Scan
rpc, factory, weth, router, lo, hi, days, out = sys.argv[1:9]; horizon = int(sys.argv[9]) if len(sys.argv) > 9 else 72000
s = Scan(rpc, factory, weth, horizon=horizon, swapwin=horizon, threads=8, log=lambda x: print(x, flush=True))
head = s.head(); b0 = head - int(float(days) * 864000); print("blocks", b0, head, flush=True)
pairs = s.pairs(b0, head); print("WETH pairs", len(pairs), flush=True)
txs = s.fill_txs([p["tx"] for p in pairs.values()])
tier = {}
for a, p in pairs.items():
    t = txs.get(p["tx"])
    if t and t[1] == router[2:].lower() and t[4] == "0xf305d719" and t[2] == 2 and float(lo) <= t[3] / 1e18 <= float(hi):
        p["from"], p["value"] = t[0], t[3] / 1e18; tier[a] = p
print("pairs of the tier", len(tier), flush=True)
s.fill_events(tier)
s.fill_txs([sw[6] for p in tier.values() for sw in p["swaps"]], txs)
json.dump({"blocks": [b0, head], "pairs": tier, "txs": {h: txs[h] for p in tier.values() for h in [p["tx"]] + [sw[6] for sw in p["swaps"]] if h in txs}}, open(out, "w"))
print("done ->", out, flush=True)
