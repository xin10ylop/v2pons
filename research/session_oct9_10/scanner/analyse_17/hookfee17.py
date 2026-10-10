"""Family 0x5bd1fbe7|a80ac0c2|1284 (hook 0x75a54357, PoolKey fee 0): read the hook's cut from receipts of a sample of the family's swaps
(buys and sells, cached), and compare the tx value with the Swap event's ETH."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
pids = F[K[2]]["pids"]; E = load_events(set(pids))
HOOK = "0x75a54357d9c78a2db19004a5fdc76c50f9242aec"
want = []
for pid in pids:
    sw = E[pid]["swaps"]
    b = [s for s in sw if s["a0"] < 0][:6]; se = [s for s in sw if s["a0"] > 0][:4]
    want += [s["tx"] for s in b + se]
want = list(dict.fromkeys(want))
CACHE = os.path.join(HERE, "hookfee_rcpts.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
miss = [h for h in want if h not in R]
if miss:
    R.update(zip(miss, batch([("eth_getTransactionReceipt", [h]) for h in miss]))); json.dump(R, open(CACHE, "w"))
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
out = []
tops = collections.Counter()
for pid in pids:
    for s in E[pid]["swaps"]:
        if s["tx"] not in R or R[s["tx"]] is None: continue
        r = R[s["tx"]]; t = T.get(s["tx"])
        hl = [l for l in r["logs"] if l["address"].lower() == HOOK]
        ev = [(l["topics"][0][:10], len(l["topics"]), [W(l["data"], i) for i in range((len(l["data"]) - 2) // 64)]) for l in hl]
        for e in ev: tops[e[0]] += 1
        row = {"pid": pid[:12], "rel": s["bn"] - P[pid]["launch_block"], "side": "buy" if s["a0"] < 0 else "sell", "a0": s["a0"], "a1": s["a1"],
               "tx_value": t["value_wei"] if t else None, "to": t["to"] if t else None, "status": r["status"], "hook_events": ev,
               "n_logs": len(r["logs"]), "log_addrs": collections.Counter(l["address"][:10] for l in r["logs"]).most_common(6)}
        if s["a0"] < 0 and t and t["value_wei"]:
            row["pool_in_over_value"] = -s["a0"] / t["value_wei"]
        for e in ev:
            if e[2] and s["a0"] < 0: row["hook_word_over_a0"] = [w / -s["a0"] for w in e[2] if w < 10**24]
            if e[2] and s["a0"] > 0: row["hook_word_over_a0"] = [w / s["a0"] for w in e[2] if w < 10**24]
        out.append(row)
for r in out: print({k: v for k, v in r.items() if k not in ("log_addrs",)})
print(tops)
json.dump(out, open(os.path.join(HERE, "hookfee.json"), "w"), indent=1)
