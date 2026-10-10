"""Sender diversity of each family's first scheduled buy (distinct wallets, how many pools each, the wallets' nonces = fresh or reused),
and the launch constants per family / sub-family (sqrtPriceX96, liquidity, range, value) for an engine recognizer."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
from analyse import sched_pred
P = load_pools(); T = load_txs(); FF = load_families(); M = load_blocks_meta()
FAMS = json.load(open(os.path.join(HERE, "families_in.json")))
out = {}
for i, f in enumerate(FAMS):
    rows = [json.loads(l) for l in open(os.path.join(HERE, f"pools_{i}.jsonl"))]
    pids = FF[f["key"]]["pids"]; E = load_events(set(pids)); is_s = sched_pred(f["name"])
    nonces = []; froms = collections.Counter(); vals = collections.Counter()
    for pid in pids:
        pl = Pool(P[pid], E[pid], T, M)
        fs = next((x for x in pl.buys() if x["to"] is not None and is_s(x)), None)
        if fs:
            t = T[fs["tx"]]; nonces.append(t["nonce"]); froms[t["from"]] += 1; vals[round(t["value_eth"], 6)] += 1
    const = collections.Counter((r["sub"], P[r["pid"]]["sqrt_p0"], r["L0"], round(P[r["pid"]]["launch_value_eth"], 6)) for r in rows)
    out[f["name"]] = {"sched_from_distinct": len(froms), "sched_pools": sum(froms.values()), "pools_per_wallet_max": max(froms.values()) if froms else None,
                      "sched_nonce_p": q(nonces, (0, .1, .5, .9, 1)), "sched_tx_value_top": vals.most_common(3),
                      "launch_constants_top": [[a, str(b), str(c), d, n] for (a, b, c, d), n in const.most_common(8)]}
    print(f["name"], json.dumps(out[f["name"]]))
json.dump(out, open(os.path.join(HERE, "senders.json"), "w"), indent=1)
