"""virtual ETH depth (L / sqrtP) at the launch state and the reference room (ETH ahead that cuts a small buy's output 1%,
the 0.99 x quote assumption) per family"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
KEYS = json.load(open(os.path.join(HERE, "keys.json")))
E = load_events(set(p for k in KEYS for p in F[k]["pids"]))
out = {}
for k in KEYS:
    d, r1, r2 = [], [], []
    for pid in F[k]["pids"]:
        pool = Pool(P[pid], E.get(pid), T, M); s, L = pool.launch_state(); fee = pool.fee_at(pool.b0)
        d.append(L * Q96 / s / 1e18)
        for X, acc in ((int(0.0058e18), r1), (int(0.05e18), r2)):
            mo = int(v4math.buy_out_int(int(s), L, X, fee) * 0.99); acc.append(room(s, L, X, fee, mo))
    out[k] = {"virtual_eth_depth_p10_50_90": q(d, nd=6), "room_0.0058_buy_p10_50_90": q(r1, nd=6), "room_0.05_buy_p10_50_90": q(r2, nd=6)}
json.dump(out, open(os.path.join(HERE, "depth.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
