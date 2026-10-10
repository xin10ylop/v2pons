import sys, os, json
sys.path.insert(0, os.getcwd())
from common21 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
for pid in ["0x48df636bfee62973fecba7da7fd5cf6b77363bfd896f2c1b4c048f08e8f6b3c2", "0xd95becfc5398b51d2b9076619c9082cc0f231200b01626067aea0d5cbab59d27"]:
    E = load_events({pid}); pl = Pool(P[pid], E[pid], T, M)
    print(pid[:10], "s_eff", pl.s_eff, "L0", pl.L0, "start", pl.start)
    for x in pl.seq: print("  ", x["bn"] - pl.b0, x["buy"], x["eth"] / 1e18, x["sqrt_p"], x["liq"], x["fee"], x["in_launch"], x.get("d_inv"), x.get("d_sp"))
    for S in (20, 500, 3000):
        print("  trade S", S, pl.trade(pl.b0 + 1, pl.b0 + S))
