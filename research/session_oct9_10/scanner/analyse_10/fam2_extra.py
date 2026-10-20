"""family 2 (graduation sniper 0x2c2572da -> hook 0xe5e70264 pools): the trades without the hook's 4% tax (what the price path alone gives),
the buys ahead of our launch+1 buy, the sells behind it, and the first-block sniper set"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
k = "0x2a53386daf0bf3eedd9e715d162649764358c7b5|3d9ab7c9|292|0|200|false"
pids = F[k]["pids"]; E = load_events(set(pids))
out = {"rows": []}
fr_tax, fr_notax, fo_notax = [], [], []
for pid in pids:
    pool = Pool(P[pid], E[pid], T, M); b0 = pool.b0; buys = pool.buys()
    B = b0 + 1
    trig = next((x for x in buys if x["bn"] > B and x["eth"] >= MIN_REAL), None)
    S = min(trig["bn"] + 1, b0 + 20) if trig else b0 + 20
    a = pool.trade(B, S)
    pool.tax = 0
    b = pool.trade(B, S)
    fr = next((x for x in buys if x["eth"] >= MIN_REAL), None)
    Bf = fr["bn"] + 1; nxt = next((x for x in buys if x["bn"] > Bf and x["eth"] >= MIN_REAL), None)
    Sf = min(nxt["bn"] + 1, Bf + 4) if nxt else Bf + 4
    c = pool.trade(Bf, Sf)
    ahead = [x for x in pool.seq if not x["relay"] and x["bn"] <= B]
    s_l, L = pool.launch_state()
    eth_depth = L * Q96 / s_l / 1e18      # virtual ETH reserve L/sqrtP
    row = {"pid": pid[:12], "eth_depth_virtual": round(eth_depth, 3), "launch_tx_buy_eth": round(sum(x["eth"] for x in pool.seq if x["in_launch"] and x["buy"]) / 1e18, 5),
           "buys_ahead_eth": round(sum(x["eth"] for x in ahead if x["buy"] and not x["in_launch"]) / 1e18, 5), "sells_ahead_eth": round(sum(x["eth"] for x in ahead if not x["buy"]) / 1e18, 5),
           "front_S": S - b0, "front_ret_tax": round(a["ret"], 4), "front_ret_notax": round(b["ret"], 4), "follow_B": Bf - b0, "follow_S": Sf - b0, "follow_ret_notax": round(c["ret"], 4),
           "swaps_B_to_S": [[x["bn"] - b0, "B" if x["buy"] else "S", round(x["eth"] / 1e18, 5)] for x in pool.seq if B < x["bn"] < S and not x["relay"]]}
    out["rows"].append(row); fr_tax.append(a); fr_notax.append(b); fo_notax.append(c)
out["front_with_tax"] = summarize(fr_tax); out["front_no_tax"] = summarize(fr_notax); out["follow_no_tax"] = summarize(fo_notax)
# who buys in the first 5 blocks (snipers), across the 9 pools
who = collections.Counter(); 
for pid in pids:
    pool = Pool(P[pid], E[pid], T, M)
    for x in pool.buys():
        if x["bn"] - pool.b0 <= 5 and x["from"]: who[(x["from"], x["to"])] += 1
out["early_buyers_first5_blocks"] = [[f, t, n] for (f, t), n in who.most_common(12)]
json.dump(out, open(os.path.join(HERE, "fam2_extra.json"), "w"), indent=1)
print(json.dumps({kk: v for kk, v in out.items() if kk != "rows"}, indent=1)); 
for r in out["rows"]: print(r)
