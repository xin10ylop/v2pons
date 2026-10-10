import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
pids = [x for k in K for x in F[k]["pids"]]
E = load_events(set(pids))
for k in K:
    f = F[k]
    print("=" * 100); print(k)
    print({kk: v for kk, v in f.items() if kk not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("-- pool", pid, "block", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "hooks", p["hooks"], "fee", p["fee"], "ts", p["tick_spacing"], "tick0", p["tick0"], "liq", p["liq_launch"], "token", p["token"], "created", p["created_contract"], "code", p["to_code_size"])
        print("   nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "npull", p["n_pulls"], "nadd", p["n_adds"], "first_buy", p["first_buy_rel"], p["first_buy_eth"], "first_pull", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"], "buy_in_launch", p["buy_in_launch_tx"])
        if not e: print("   no events"); continue
        for a in e["adds"]: print("   add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["tx"][:12], a["sender"][:12])
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print("   swap +%d ti%d li%d a0 %.8f a1 %d fee %d sp %d liq %d tick %d" % (s["bn"] - p["launch_block"], s["ti"], s["li"], s["a0"] / 1e18, s["a1"], s["fee"], s["sqrt_p"], s["liq"], s["tick"]),
                  (t["from"][:12], (t["to"] or "")[:12], t["selector"], t["calldata_len"], t["nonce"], t["value_eth"]) if t else s["sender"][:12])
        if len(e["swaps"]) > 14: print("   ... %d more swaps" % (len(e["swaps"]) - 14))
        for a in e["pulls"][:3]: print("   pull", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["tx"][:12], a["sender"][:12])
        print("   zero_mods", len(e["zero_mods"]))
