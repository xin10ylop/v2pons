import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
K = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_15/keys.json"))
pids = set(p for k in K for p in F[k]["pids"])
E = load_events(pids)
print(list(F[K[0]].keys()))
for k in K:
    print("=====", k)
    for pid in F[k]["pids"]:
        p = P[pid]; e = E.get(pid)
        print(pid[:12], p["launch_block"], p["launch_ts"], "from", p["launch_from"][:10], "n", p["launch_nonce"], "val", p["launch_value_eth"], "tick0", p["tick0"], "hooks", p["hooks"][:10], "tok", p["token"][:10],
              "nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "np", p["n_pulls"], "na", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first_pull_from"] and p["first_pull_from"][:10], p["first_pull_to"] and p["first_pull_to"][:10], p["first_pull_selector"], "liq", p["liq_launch"], "bilt", p["buy_in_launch_tx"])
        if e:
            for a in e["adds"][:3]: print("    add", a["bn"]-p["launch_block"], a["lo"], a["hi"], a["dl"], a["tx"][:10])
            for s in e["swaps"][:12]:
                t = T.get(s["tx"])
                print("    sw", s["bn"]-p["launch_block"], s["ti"], s["a0"]/1e18, s["fee"], s["sender"][:10], t and t["from"][:10], t and t["to"] and t["to"][:10], t and t["selector"], t and t["calldata_len"], t and t["nonce"])
            for s in e["pulls"][:3]: print("    pull", s["bn"]-p["launch_block"], s["dl"], s["sender"][:10], s["tx"][:10])
