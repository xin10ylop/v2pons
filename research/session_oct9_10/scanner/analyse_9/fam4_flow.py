import sys, json, collections, statistics as st
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
keys = ["create|60808060|3740|2500|25|true", "create|60808060|3708|2500|25|true"]
pids = [pid for k in keys for pid in F[k]["pids"]]
E = load_events(set(pids))
out = {"pools": []}
wallets = collections.Counter()
hold_N = [5, 10, 20, 50, 100, 200, 300, 500, 1000, 2000, 2990]
holds = {N: [] for N in hold_N}
for pid in pids:
    pl = Pool(P[pid], E.get(pid), T, M)
    bs = pl.buys(); ss = [x for x in pl.seq if not x["buy"]]
    big_sells = [(x["bn"] - pl.b0, round(x["eth"] / 1e18, 4), x["from"]) for x in ss if x["eth"] > int(0.1e18)]
    for x in pl.seq[:8]:
        if x["buy"] and not x["in_launch"]: wallets[x["from"]] += 1
    # price path: tokens bought at +1 by 0.0058 and the value at the head of block N (replay)
    row = {"pid": pid[:12], "key_len": P[pid]["calldata_len"], "dev": P[pid]["launch_from"][:10], "val": P[pid]["launch_value_eth"],
           "n_buys": len(bs), "eth_buys": round(sum(x["eth"] for x in bs) / 1e18, 4), "n_sells": len(ss), "eth_sells": round(sum(x["eth"] for x in ss) / 1e18, 4),
           "big_sells": big_sells[:6], "adds_later": [(a["bn"] - pl.b0, a["dl"]) for a in E[pid]["adds"][1:]], "pulls": len(pl.pulls),
           "buys_by_1000": len([x for x in bs if x["bn"] - pl.b0 <= 1000]), "last_swap_rel": pl.seq[-1]["bn"] - pl.b0 if pl.seq else None}
    row["hold"] = {}
    for N in hold_N:
        r = pl.trade(pl.b0 + 1, pl.b0 + N); holds[N].append(r); row["hold"][N] = round(r["ret"], 4)
    out["pools"].append(row)
out["hold_summary"] = {N: summarize(holds[N]) for N in hold_N}
out["first8_buyers"] = wallets.most_common(25)
json.dump(out, open("fam4_flow.json", "w"), indent=1, default=str)
for r in out["pools"]: print(json.dumps(r, default=str))
for N in hold_N:
    s = out["hold_summary"][N]; print("hold +%d: n %d mean %+.4f median %+.4f win %.2f min %+.4f max %+.4f" % (N, s["n"], s["mean"], s["median"], s["win"], s["min"], s["max"]))
print(out["first8_buyers"])
