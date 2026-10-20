"""Family 0xc763b179|f0e9eabf|1828 (hook 0xae4c0cf7): read the hook's fee from the receipts of every swap of the family (one POST, cached),
and compare with the tx value / Swap-event ratio (router 0xf0b7eaaf takes 1% of the tx value first: analyse_1)."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
pids = F[K[1]]["pids"]; E = load_events(set(pids))
HOOK = "0xae4c0cf7c3feb79e0c244edbc6a3f8a3290940cc"
want = [s["tx"] for pid in pids for s in E[pid]["swaps"]]
CACHE = os.path.join(HERE, "hookfee_rcpts.json")
if os.path.exists(CACHE): R = json.load(open(CACHE))
else:
    R = dict(zip(want, batch([("eth_getTransactionReceipt", [h]) for h in want]))); json.dump(R, open(CACHE, "w"))
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
out = []
for pid in pids:
    for s in E[pid]["swaps"]:
        r = R[s["tx"]]; t = T.get(s["tx"])
        hl = [l for l in r["logs"] if l["address"] == HOOK]
        ev = [(l["topics"][0][:10], [W(l["data"], i) for i in range((len(l["data"]) - 2) // 64)]) for l in hl]
        row = {"pid": pid[:12], "rel": s["bn"] - P[pid]["launch_block"], "side": "buy" if s["a0"] < 0 else "sell", "a0": s["a0"], "a1": s["a1"],
               "tx_value": t["value_wei"] if t else None, "to": t["to"] if t else None, "status": r["status"], "hook_events": ev}
        if s["a0"] < 0 and t and t["value_wei"]:
            row["pool_in_over_value"] = -s["a0"] / t["value_wei"]
        for top, d in ev:
            if top == "0x8d1f1ed7": row["hook_rate"] = d[2] / (d[0] + d[2])
            if top == "0x5a2eb160": row["hook_rate"] = d[2] / d[1]
        out.append(row); print(row)
json.dump(out, open(os.path.join(HERE, "hookfee.json"), "w"), indent=1)
