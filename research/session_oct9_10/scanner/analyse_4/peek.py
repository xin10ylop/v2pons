import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = ["0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|100000|200|false",
"0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|838974|9303|true",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|3000|60|true",
"0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|769|30000|200|true"]
for k in KEYS:
    f = F[k]
    print("=" * 100); print(k)
    print({a: b for a, b in f.items() if a != "pids"})
    for pid in f["pids"]:
        p = P[pid]
        print(f"  {pid[:12]} b{p['launch_block']} ts{p['launch_ts']} from {p['launch_from'][:10]} n{p['launch_nonce']} v{p['launch_value_eth']} hooks {p['hooks'][:10]} tick0 {p['tick0']} liq {p['liq_launch']} sw {p['n_swaps']} b{p['n_buys']} s{p['n_sells']} pull {p['n_pulls']} add {p['n_adds']} ethin {p['eth_in_buys']:.4f} fb {p['first_buy_rel']} {p['first_buy_eth']} fp {p['first_pull_rel']} {p['first_pull_to'] and p['first_pull_to'][:10]} {p['first_pull_selector']} {p['first_pull_from'] and p['first_pull_from'][:10]} inl {p['buy_in_launch_tx']} to8 {[t and t[:8] for t in (p['first8_swap_to'] or [])]}")
