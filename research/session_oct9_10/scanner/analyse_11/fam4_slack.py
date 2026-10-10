"""family 4: the realised output of the 0.04777 ETH buys (and of each pool's first real buy) over their launch-state quote: a lower bound on
the slack their minOut allows (their calldata is a nested UR execute / undecoded router, so minOut itself is not read)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
key = json.load(open(os.path.join(HERE, "keys.json")))[3]
pids = F[key]["pids"]; E = load_events(set(pids))
out = []
for pid in pids:
    pool = Pool(P[pid], E[pid], T, M)
    s_l, L_l = pool.launch_state()
    buys = pool.buys()
    fr = next(x for x in buys if x["eth"] >= MIN_REAL)
    b7 = next((x for x in buys if abs(x["eth"] - 47_770_000_000_000_000) < 10**9), None)
    row = {"pid": pid[:12]}
    for name, x in (("first_real", fr), ("b0.04777", b7)):
        if x is None: continue
        quote = v4math.buy_out_int(int(s_l), L_l, x["eth"], x["fee"])
        ahead = sum(y["eth"] for y in buys if (y["bn"], y["li"]) < (x["bn"], x["li"])) / 1e18
        row[name] = {"rel": x["bn"] - pool.b0, "eth": x["eth"] / 1e18, "fill_over_launch_quote": round(x["a1"] / quote, 4), "eth_bought_ahead": round(ahead, 4)}
    out.append(row)
json.dump(out, open(os.path.join(HERE, "fam4_slack.json"), "w"), indent=1)
for r in out: print(r)
