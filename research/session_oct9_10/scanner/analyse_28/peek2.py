import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
f1 = [p for p in P.values() if p["selector"] == "ec64ddcf" and p["calldata_len"] == 196 and p["fee"] == 0 and p["tick_spacing"] == 60 and not p["hooks_zero"]]
f2 = [p for p in P.values() if (p["to_code_hash"] or "").startswith("8ce82419") and p["selector"] == "bc9d39fd" and p["fee"] == 0 and p["tick_spacing"] == 200 and not p["hooks_zero"]]
print(len(f1), len(f2))
json.dump({"F1": [p["pid"] for p in f1], "F2": [p["pid"] for p in f2]}, open("pids.json", "w"))
for name, f in (("F1", f1), ("F2", f2)):
    print("=====", name)
    c = collections.Counter
    print("hooks", c(p["hooks"] for p in f).most_common(8))
    print("from", c(p["launch_from"] for p in f).most_common(8))
    print("to_code", c((p["to_code_size"], (p["to_code_hash"] or "")[:8]) for p in f).most_common(8))
    print("created", c(p["created_contract"] is not None for p in f), "launch_to null", c(p["launch_to"] is None for p in f))
    print("nonce", sorted(p["launch_nonce"] for p in f)[:10], "value", c(p["launch_value_eth"] for p in f))
    print("calldata_len", c(p["calldata_len"] for p in f).most_common(10))
    print("sqrt_p0", c(p["sqrt_p0"] for p in f).most_common(5)); print("tick0", c(p["tick0"] for p in f).most_common(5))
    print("liq_launch", c(p["liq_launch"] for p in f).most_common(5))
    print("blocks", min(p["launch_block"] for p in f), max(p["launch_block"] for p in f))
    for p in f[:80]:
        print(p["pid"][:10], p["launch_block"], p["launch_ts"], p["launch_from"][:10], (p["launch_to"] or "")[:10], p["launch_nonce"], p["tick0"], p["liq_launch"], "sw", p["n_swaps"], "b", p["n_buys"], "s", p["n_sells"], "pl", p["n_pulls"], "add", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"], (p["first_pull_to"] or "")[:10], p["first_pull_selector"], (p["first_pull_from"] or "")[:10], "inl", p["buy_in_launch_tx"], [ (x or "")[:8] for x in (p["first8_swap_to"] or [])])
