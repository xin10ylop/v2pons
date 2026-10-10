import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = ["0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true",
"0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true",
"0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true",
"0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true"]
for k in KEYS:
    f = F[k]
    print("=====", k)
    print({a: b for a, b in f.items() if a not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]
        print(pid[:12], p["launch_block"], p["launch_ts"], p["launch_from"][:10], p["launch_nonce"], p["launch_value_eth"], "tok", p["token"][:10], "tick0", p["tick0"], "nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "np", p["n_pulls"], "na", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first_pull_to"] and p["first_pull_to"][:10], p["first_pull_selector"], p["first_pull_from"] and p["first_pull_from"][:10], "liq", p["liq_launch"], "bilt", p["buy_in_launch_tx"], [x and x[:10] for x in p["first8_swap_to"]])
