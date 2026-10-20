import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common19 import *
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
for k in K:
    f = F[k]; print("=" * 100); print(k)
    print({a: f.get(a) for a in ("count", "values_eth", "value_counts", "known", "known_by_rule", "n_deployers", "top_deployers", "nonce_med", "first_block", "last_block", "to_code_size", "to_code_hash", "swap_tx_to_top", "first_pull_to_sel_top", "first_buy_rel_p10_50_90", "first_pull_rel_p10_50_90", "first_buy_eth_p10_50_90", "n_no_pull_in_window", "hooks", "vbot_router_buy_pools")})
    E = load_events(set(f["pids"]))
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid) or {}
        print(" pid", pid[:12], "bn", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tick0", p["tick0"], "liq", p["liq_launch"], "hooks", p["hooks"][:10], "token", p["token"][:10])
        print("   swaps", p["n_swaps"], "buys", p["n_buys"], "sells", p["n_sells"], "pulls", p["n_pulls"], "adds", p["n_adds"], "eth_in", round(p["eth_in_buys"], 6), "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], (p["first_pull_from"] or "")[:10], "bilt", p["buy_in_launch_tx"])
        for a in e.get("adds", [])[:3]: print("   add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
        for s in e.get("swaps", [])[:12]:
            t = T.get(s["tx"])
            print("   sw +%d ti%d %s eth %.6f fee %d sender %s to %s from %s sel %s clen %s" % (s["bn"] - p["launch_block"], s["ti"], "BUY " if s["a0"] < 0 else "SELL", abs(s["a0"]) / 1e18, s["fee"], s["sender"][:10], (t or {}).get("to", "?") and (t or {}).get("to", "?")[:10], (t or {}).get("from", "?")[:10], (t or {}).get("selector"), (t or {}).get("calldata_len")))
        for s in e.get("pulls", [])[:3]: print("   pull +%d dl %d sender %s tx %s" % (s["bn"] - p["launch_block"], s["dl"], s["sender"][:10], s["tx"][:10]))
