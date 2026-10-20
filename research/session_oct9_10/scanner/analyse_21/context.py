import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
out = {}
for k in K:
    f = F[k]; deps = set(P[x]["launch_from"] for x in f["pids"])
    tos = set(P[x]["launch_to"] for x in f["pids"])
    byd = [p for p in P.values() if p["launch_from"] in deps]
    byto = [p for p in P.values() if p["launch_to"] in tos] if "0x58daec31" not in k else []
    r = {"deployers": sorted(deps), "pools_by_deployers": len(byd),
         "by_deployer_fam": collections.Counter(p["family"] for p in byd).most_common(12),
         "by_deployer_known": collections.Counter(p["known"] for p in byd).most_common(),
         "by_deployer_fee": collections.Counter((p["fee"], p["tick_spacing"]) for p in byd).most_common(12),
         "pools_by_launch_to": len(byto), "by_to_fam": collections.Counter(p["family"] for p in byto).most_common(6)}
    # per deployer counts
    r["per_deployer"] = {d: [sum(1 for p in byd if p["launch_from"] == d), sorted(collections.Counter(p["fee"] for p in byd if p["launch_from"] == d).items())[:10],
                             [min(p["launch_nonce"] for p in byd if p["launch_from"] == d), max(p["launch_nonce"] for p in byd if p["launch_from"] == d)]] for d in deps}
    # swaps in by-deployer pools
    nsw = sum(p["n_swaps"] for p in byd); npl = sum(1 for p in byd if p["n_pulls"]); nb = sum(1 for p in byd if p["n_buys"])
    r["by_deployer_swaps_total"] = nsw; r["by_deployer_pools_with_buy"] = nb; r["by_deployer_pools_pulled"] = npl
    r["by_deployer_first_buy_rel"] = sorted([p["first_buy_rel"] for p in byd if p["first_buy_rel"] is not None])[:40]
    r["by_deployer_values"] = collections.Counter(round(p["launch_value_eth"], 4) for p in byd).most_common(8)
    out[k] = r
    print("=" * 90); print(k)
    for kk, v in r.items(): print("  ", kk, v)
json.dump(out, open("context.json", "w"), indent=1, default=str)
