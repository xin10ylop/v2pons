"""Context for the assigned fragments: the whole 0x06cb3a68 operator (every pool it launched in the census) and the whole 0xc763b179 launchpad
(every pool through it: launcher -> first-buyer pairing, offsets, sizes, pulls). Writes context.json."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common15 import *  # noqa
P = load_pools(); T = load_txs()
out = {}
op = [r for r in P.values() if r["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"]
E = load_events(set(r["pid"] for r in op))
real = []
for r in op:
    e = E.get(r["pid"]) or {"swaps": []}
    rb = [s for s in e["swaps"] if s["a0"] < 0 and -s["a0"] >= MIN_REAL]
    if rb: real.append((r["pid"][:12], rb[0]["bn"] - r["launch_block"], -rb[0]["a0"] / 1e18))
bs = sorted(r["launch_block"] for r in op)
out["op_06cb3a68"] = {"pools": len(op), "launch_contracts": len(set(r["launch_to"] for r in op)), "families": len(set(r["family"] for r in op)),
                      "selectors": collections.Counter(r["selector"] for r in op).most_common(3), "fee_ts": collections.Counter((r["fee"], r["tick_spacing"]) for r in op).most_common(3),
                      "tick0": collections.Counter(r["tick0"] for r in op).most_common(3), "liq": collections.Counter(r["liq_launch"] for r in op).most_common(2),
                      "pools_with_real_buy": len(real), "real_buys": real[:10], "pulled": sum(1 for r in op if r["first_pull_rel"] is not None),
                      "n_swaps": collections.Counter(r["n_swaps"] for r in op).most_common(5), "per_day": round(len(op) / WINDOW_DAYS, 1),
                      "gap_blocks_p10_50_90": q([b - a for a, b in zip(bs, bs[1:])]), "nonce_range": [min(r["launch_nonce"] for r in op), max(r["launch_nonce"] for r in op)]}
print(json.dumps(out["op_06cb3a68"]))
lp = [r for r in P.values() if r["launch_to"] == "0xc763b1795dabe2d2336eba214d16969ebc5db27f"]
E2 = load_events(set(r["pid"] for r in lp))
pair = collections.defaultdict(collections.Counter); offs = []; sizes = []; withb = 0
for r in lp:
    e = E2.get(r["pid"]) or {"swaps": []}
    rb = [s for s in e["swaps"] if s["a0"] < 0 and -s["a0"] >= MIN_REAL]
    if not rb: continue
    withb += 1; t = T.get(rb[0]["tx"])
    pair[r["launch_from"]][t["from"] if t else None] += 1
    offs.append(rb[0]["bn"] - r["launch_block"]); sizes.append(-rb[0]["a0"] / 1e18)
out["launchpad_c763b179"] = {"pools": len(lp), "launchers": len(set(r["launch_from"] for r in lp)), "pools_with_real_buy": withb, "first_real_rel_p10_50_90": q(offs),
                             "first_real_eth_p10_50_90": q(sizes), "pulled": sum(1 for r in lp if r["first_pull_rel"] is not None),
                             "launcher_to_first_buyer": {k: dict(v) for k, v in sorted(pair.items(), key=lambda kv: -sum(kv[1].values()))[:10]},
                             "per_day": round(len(lp) / WINDOW_DAYS, 1)}
print(json.dumps(out["launchpad_c763b179"]))
fp = [r for r in P.values() if r["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and r["calldata_len"] == 2020]
out["posm_2020"] = {"pools": len(fp), "launchers": len(set(r["launch_from"] for r in fp)), "fee_tiers": len(set(r["fee"] for r in fp)),
                    "with_real_first_buy": sum(1 for r in fp if (r["first_buy_eth"] or 0) >= 0.0002), "pulled": sum(1 for r in fp if r["first_pull_rel"] is not None)}
print(json.dumps(out["posm_2020"]))
json.dump(out, open(os.path.join(HERE, "context.json"), "w"), indent=1, default=str)
