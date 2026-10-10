import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); T = load_txs()
keys = json.load(open("families_in.json"))
for k in keys:
    f = F[k]
    print("=" * 30, k)
    print({x: f[x] for x in f if x not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]
        print(pid[:10], p["launch_block"], p["launch_ts"], p["launch_from"], p["launch_nonce"], p["launch_value_eth"], p["fee"], p["tick_spacing"], p["tick0"], p["liq_launch"],
              "sw", p["n_swaps"], "b", p["n_buys"], "s", p["n_sells"], "pull", p["n_pulls"], "adds", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first8_swap_to"][:4], p["eth_in_buys"])
