import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
pids = set(x for k in K for x in F[k]["pids"])
E = load_events(pids)
for k in K:
    f = F[k]
    print("=" * 100); print(k)
    print({a: b for a, b in f.items() if a not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print(" pool", pid[:12], "b0", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "ti", p["tx_index"], "tick0", p["tick0"], "liq", p["liq_launch"], "token", p["token"])
        print("    nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "npull", p["n_pulls"], "nadd", p["n_adds"], "ethin", p["eth_in_buys"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fpull", p["first_pull_rel"], p["first_pull_from"], p["first_pull_to"], p["first8_swap_to"])
        if e:
            for a in e["adds"]: print("    add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"], a["tx"] == p["launch_tx"])
            for s in e["swaps"][:12]:
                t = T.get(s["tx"])
                print("    sw +%d ti %d a0 %.8f a1 %d fee %d sender %s to %s from %s sel %s" % (s["bn"] - p["launch_block"], s["ti"], s["a0"] / 1e18, s["a1"], s["fee"], s["sender"][:10], t and t["to"], t and t["from"], t and t["selector"]))
            for x in e["pulls"]: print("    pull +%d" % (x["bn"] - p["launch_block"]), x["dl"], x["sender"])
