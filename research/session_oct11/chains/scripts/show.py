"""Print compact per-venue results from a run log."""
import sys, json
for line in open(sys.argv[1]):
    if not line.startswith("{"):
        if line.startswith(("soneium", "Traceback", "  File", "rpc.", "Error", "requests")) or "Error" in line: print(line.rstrip()[:400])
        continue
    try: d = json.loads(line)
    except Exception: print(line[:300]); continue
    if "venue" not in d: print(str(d)[:300]); continue
    print(d["chain"], d["venue"], "n", d["n_creations"], "hrs", d["covered_hours"], "perday", d["per_day"], "sampled", d["n_sampled"], "traded", d["n_traded_in_W"], "launchtxswap", d["launch_tx_contains_swap"], "medoff", d["median_offset_first_external_swap"])
    print("   offs", d["first3_offsets_excl_launch_tx"][:30])
    print("   to", d["first3_tx_to_by_launches"][:4])
    print("   from", d["first3_tx_from_by_launches"][:4])
    print("   sender", d["first3_swap_sender_by_launches"][:3])
    print("   wallets", d["wallets_first3blocks_excl_launch_tx"], "gas", d["gasPrice_gwei_median"], "launchto", d["launch_tx_to_counts"][:3], "hooks", d["top_hooks"][:3], "err", d["errlog"][:2])
