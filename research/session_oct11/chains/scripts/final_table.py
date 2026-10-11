"""Per-chain roll-up of discovery counts, venue samples, block time and gas (all from out/*.json)."""
import json, glob, os, collections
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
gas = json.load(open(os.path.join(OUT, "gas_blocktime.json")))
summ = json.load(open(os.path.join(OUT, "summary.json")))
disc = {os.path.basename(f)[9:-5]: json.load(open(f)) for f in glob.glob(os.path.join(OUT, "discover_*.json"))}
by = collections.defaultdict(list)
for r in summ: by[r["chain"]].append(r)
lines = []
for ch in ["base", "bnb", "unichain", "optimism", "ink", "soneium", "worldchain", "mode", "megaeth", "monad", "apechain", "xai", "reya"]:
    g = gas.get(ch, {})
    d = disc.get(ch)
    dtxt = f"all-emitter creations {d['n_logs']} in {d['hours']}h" if d else "no all-emitter scan"
    lines.append(f"## {ch}: block {g.get('block_time_s')}s, gas/swap {g.get('native_per_swap')} {g.get('native')} (${g.get('usd_per_swap')}, {g.get('gas_src')}); {dtxt}")
    for r in by.get(ch, []):
        lines.append(f"   {r['venue']}: {r['per_day']}/day (cov {r['covered_h']}h) sampled {r['sampled']} traded {r['traded_in_W']} in {r['W']} blk; "
                     f"med first ext swap offset {r['median_first_ext_swap_offset']}; wallets first 3 blk med(traded) {r['median_wallets_3blk_traded']} max {r['max_wallets_3blk']}; "
                     f"recurring tx.to {r['recurring_tx_to(>=3 launches)']}; top tx.from {r['top_tx_from'][:2]}")
open(os.path.join(OUT, "final_table.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
