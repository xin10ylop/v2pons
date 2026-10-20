import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
FK = json.load(open("families_in.json"))
F = load_families(); P = load_pools(); T = load_txs()
pids = set(); 
for k in FK: pids |= set(F[k]["pids"])
E = load_events(pids)
for k in FK:
    f = F[k]
    print("=" * 100); print(k)
    print({a: f[a] for a in f if a not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("-- pool", pid[:12], "bn", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tick0", p["tick0"], "liq", p["liq_launch"], "token", p["token"], "created", p["created_contract"])
        print("   n_swaps", p["n_swaps"], "buys", p["n_buys"], "sells", p["n_sells"], "pulls", p["n_pulls"], "adds", p["n_adds"], "fb_rel", p["first_buy_rel"], "fb_eth", p["first_buy_eth"], "pull_rel", p["first_pull_rel"], "pull_to", p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
        if not e: print("   no events"); continue
        for a in e["adds"][:4]: print("   add", a["bn"] - p["launch_block"], a["ti"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print("   swap +%d ti %d %s a0 %.6f fee %d sender %s to %s from %s sel %s" % (s["bn"] - p["launch_block"], s["ti"], "BUY " if s["a0"] < 0 else "SELL", -s["a0"] / 1e18, s["fee"], s["sender"][:10], (t or {}).get("to"), (t or {}).get("from"), (t or {}).get("selector")))
        for u in e["pulls"][:3]: print("   pull", u["bn"] - p["launch_block"], u["dl"], u["sender"][:10], u["tx"][:10])
