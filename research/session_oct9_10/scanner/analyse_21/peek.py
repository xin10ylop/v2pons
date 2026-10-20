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
    print({kk: v for kk, v in f.items() if kk not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid) or {}
        print("-- pool", pid, "lb", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "token", p["token"])
        print("   fee", p["fee"], "ts", p["tick_spacing"], "tick0", p["tick0"], "sp0", p["sqrt_p0"], "liq_launch", p["liq_launch"], "to_code", p["to_code_size"], p["created_contract"])
        print("   n_swaps", p["n_swaps"], "buys", p["n_buys"], "sells", p["n_sells"], "pulls", p["n_pulls"], "adds", p["n_adds"], "first_buy_rel", p["first_buy_rel"], p["first_buy_eth"], "first_pull_rel", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
        for a in e.get("adds", [])[:4]: print("   add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"], a["tx"][:12])
        for a in e.get("pulls", [])[:3]: print("   pull", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"], a["tx"][:12])
        for s in e.get("swaps", [])[:14]:
            t = T.get(s["tx"])
            print("   swap +%d ti%d a0 %.8f a1 %d fee %d liq %d" % (s["bn"] - p["launch_block"], s["ti"], -s["a0"] / 1e18, s["a1"], s["fee"], s["liq"]), s["sender"][:10], (t["to"], t["from"], t["selector"], t["nonce"], t["calldata_len"]) if t else None)
        if len(e.get("swaps", [])) > 14: print("   ...", len(e["swaps"]), "swaps")
