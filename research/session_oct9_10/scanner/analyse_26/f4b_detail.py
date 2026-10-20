import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common26 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
F4b = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1 and not p["hooks_zero"]]
E = load_events(set(F4b))
def real_buys(pl, after=None):
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]
for pid in F4b:
    pl = Pool(P[pid], E[pid], T, M); lb = live_block(pl); rb = real_buys(pl)
    sends = collections.Counter(s["sender"][:8] + ("B" if s["a0"] < 0 else "S") for s in E[pid]["swaps"])
    if not rb: print(pid[:10], "no buys", sends.most_common(3)); continue
    trig = rb[0]; B = trig["bn"] + 1; nxt = next((x for x in rb if x["bn"] > B), None)
    S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + 4) else B + 4
    r = pl.trade(B, S)
    first = [(x["bn"] - lb, round(x["eth"] / 1e18, 4)) for x in rb[:8]]
    print(pid[:10], "ts", P[pid]["launch_ts"], "trig +%d" % (trig["bn"] - lb), "S +%d" % (S - lb), "ret %+.2f%%" % (100 * r["ret"]), "first real buys", first, "| senders", sends.most_common(4))
