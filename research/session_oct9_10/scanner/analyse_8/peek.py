import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
keys = ["0xcd1e2cbeda788d2c59b049b5f63810892614182e|7fde822e|804|10000|200|true",
"0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true",
"0x2b0c777574bd65ed74b211e0f2bf79bd3c9bff20|7fde822e|804|10000|200|true",
"0x80521fc999a81e467696fd834d1df0a082d01894|7fde822e|804|10000|200|true"]
for k in keys:
    f = F[k]
    print("=====", k)
    print(json.dumps({x: f[x] for x in f if x != "pids"}, default=str)[:2500])
    for pid in f["pids"]:
        p = P[pid]
        print(" ", pid[:10], p["launch_block"], p["launch_ts"], p["launch_from"][:10], p["launch_nonce"], p["token"][:10], p["tick0"], p["sqrt_p0"], p["liq_launch"], "sw", p["n_swaps"], "b", p["n_buys"], "s", p["n_sells"], "pull", p["n_pulls"], "adds", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], p["first8_swap_to"][:4] if p["first8_swap_to"] else None, p["created_contract"], p["to_code_size"])
