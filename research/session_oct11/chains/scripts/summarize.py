"""Aggregate sample_*.json into a compact table; label known router contracts from docs-derived lists."""
import json, glob, os, collections
here = os.path.dirname(__file__); OUT = os.path.join(here, "..", "out")
dep = json.load(open(os.path.join(here, "..", "dl", "deployments.json")))["records"]
LABEL = {}
for r in dep:
    if r.get("env") == "mainnet" and r.get("address"):
        LABEL[r["address"].lower()] = "Uniswap " + r["contract"]
EXTRA = {  # from official docs fetched in this survey
 "0xd9c500dff816a1da21a48a732d3498bf09dc9aeb": "PancakeSwap UniversalRouter",
 "0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "PancakeSwap SmartRouter",
 "0x5c952063c7fc8610ffdb798152d69f0b9550762b": "four.meme TokenManager2",
 "0xe5bbef8de2db447a7432a47eba58924d94ee470e": "Kumbaya SwapRouter02",
 "0xaab1c664cead881afbb58555e6a3a79523d3e4c0": "Kumbaya UniversalRouter",
 "0x69fe0908f1211de66f7067021998f28a5693abbd": "Kumbaya FireLaunch",
 "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789": "ERC-4337 EntryPoint v0.6",
 "0x10ed43c718714eb63d5aa57b78b54704e256024e": "PancakeSwap V2 Router",
 "0xca143ce32fe78f1f7019d7d551a6402fc5350c73": "PancakeSwap V2 Factory",
 "0x0000000071727de22e5e9d8baf0edac6f37da032": "ERC-4337 EntryPoint v0.7",
 "0x4337084d9e255ff0702461cf8895ce9e3b5ff108": "ERC-4337 EntryPoint v0.8",
}
LABEL.update(EXTRA)
prices = json.load(open(os.path.join(OUT, "prices.json"))) if os.path.exists(os.path.join(OUT, "prices.json")) else {}
NATIVE = {"bnb": "BNB_USD", "monad": None, "apechain": None}
GAS_UNITS = 150_000  # assumed gas units for a typical single-hop swap (receipts not fetched: method not in allowed list)
rows = []
for fn in sorted(glob.glob(os.path.join(OUT, "sample_*.json"))):
    s = json.load(open(fn))
    lab = lambda a: f"{a[:10]}({LABEL.get(a, 'unlabelled')})"
    rec = [(lab(a), n) for a, n in s["first3_tx_to_by_launches"] if n >= 3]
    gp = s.get("gasPrice_gwei_median")
    px = prices.get(NATIVE.get(s["chain"], "ETH_USD")) if NATIVE.get(s["chain"], "ETH_USD") else None
    usd = gp * 1e-9 * GAS_UNITS * px if (gp is not None and px and s["chain"] not in ("apechain",)) else None
    rows.append({"chain": s["chain"], "venue": s["venue"], "per_day": s["per_day"], "covered_h": s["covered_hours"],
                 "n_creations": s["n_creations"], "sampled": s["n_sampled"], "traded_in_W": s["n_traded_in_W"], "W": s["W_blocks"],
                 "launch_tx_has_swap": s["launch_tx_contains_swap"],
                 "median_first_ext_swap_offset": s["median_offset_first_external_swap"],
                 "recurring_tx_to(>=3 launches)": rec,
                 "top_tx_to": [(lab(a), n) for a, n in s["first3_tx_to_by_launches"][:3]],
                 "top_tx_from": [(a[:10], n) for a, n in s["first3_tx_from_by_launches"][:3]],
                 "median_wallets_3blk_all": s["median_wallets_first3blocks_excl_launch_tx"],
                 "median_wallets_3blk_traded": s["median_wallets_first3blocks_traded_only"],
                 "max_wallets_3blk": max(s["wallets_first3blocks_excl_launch_tx"] or [0]),
                 "gas_gwei_median": gp, "swap_usd_at_150k_gas": round(usd, 5) if usd is not None else None,
                 "top_hooks": [(h[:10], LABEL.get(h, ""), n) for h, n in s.get("top_hooks", [])[:3]]})
json.dump(rows, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
for r in rows: print(json.dumps(r))
