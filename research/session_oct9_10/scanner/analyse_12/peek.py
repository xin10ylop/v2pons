import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = ["0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|804|10000|200|true",
"0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false",
"0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true",
"0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"]
for k in KEYS:
    f = F[k]
    print("=====", k)
    print({a: b for a, b in f.items() if a != "pids"})
    for pid in f["pids"]:
        p = P[pid]
        print(" ", pid[:12], p["launch_block"], p["launch_ts"], p["launch_from"][:10], p["launch_nonce"], p["launch_value_eth"], p["hooks"][:12], "tick0", p["tick0"], "liq", p["liq_launch"], "sw", p["n_swaps"], "b", p["n_buys"], "s", p["n_sells"], "pull", p["n_pulls"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first_pull_from"] and p["first_pull_from"][:10], p["first_pull_to"] and p["first_pull_to"][:10], p["first_pull_selector"], "bilt", p["buy_in_launch_tx"], "eth_in", p["eth_in_buys"])
        print("    swap_to", [x and x[:10] for x in p["first8_swap_to"]])
