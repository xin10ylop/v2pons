import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common26 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
F1 = [p["pid"] for p in P.values() if p["calldata_len"] == 54500]
E = load_events(set(F1[:3]))
for pid in F1[:3]:
    e = E[pid]; print(pid[:10], "fee key", P[pid]["fee"], "swap fees", collections.Counter(s["fee"] for s in e["swaps"]), "token", P[pid]["token"])
    pl = Pool(P[pid], e, T, M); r = pl.trade(pl.b0 + 1, pl.b0 + 20); print("  ", r)
    s, L = pl.state_through(pl.b0 + 1); fb = pl.fee_at(pl.b0 + 1)
    tok = v4math.buy_out_int(int(s), L, STAKE, fb); s2 = Q96 / (Q96 / s + net_in(STAKE, fb) / L)
    back = v4math.sell_out_int(int(s2), L, tok, fb); print("   round trip", back / STAKE - 1, "fee", fb)
