import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
pids = set(x for k in K for x in F[k]["pids"])
E = load_events(pids)
for k in K:
    f = F[k]
    print("=" * 100); print(k)
    print({a: f[a] for a in f if a not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("-- pool", pid, "b0", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "token", p["token"], "tick0", p["tick0"], "liq_launch", p["liq_launch"], "sqrt", p["sqrt_p0"])
        print("   n_swaps", p["n_swaps"], "buys", p["n_buys"], "sells", p["n_sells"], "pulls", p["n_pulls"], "adds", p["n_adds"], "eth_in_buys", p["eth_in_buys"], "first_buy", p["first_buy_rel"], p["first_buy_eth"], "first_pull", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
        if not e: continue
        for a in e["adds"]: print("   add", a["bn"]-p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"], a["tx"][:12])
        for s in e["swaps"][:20]:
            t = T.get(s["tx"])
            print("   swap +%d ti%d %s a0 %.6g a1 %d fee %d liq %d sender %s | %s" % (s["bn"]-p["launch_block"], s["ti"], "BUY " if s["a0"]<0 else "SELL", abs(s["a0"])/1e18, s["a1"], s["fee"], s["liq"], s["sender"][:10],
                  (t["from"][:10] + " -> " + str(t["to"])[:10] + " " + t["selector"] + " len" + str(t["calldata_len"]) + " nonce" + str(t["nonce"]) + " val" + str(t["value_eth"])) if t else "-"))
        if len(e["swaps"]) > 20: print("   ... %d swaps" % len(e["swaps"]))
        for a in e["pulls"]: print("   pull +%d" % (a["bn"]-p["launch_block"]), a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12])
