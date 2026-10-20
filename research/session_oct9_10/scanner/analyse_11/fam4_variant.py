"""family 4 (launcher 0x387a453d, hook 0xe5e70264): treat the recurring 0.04777 ETH buyer (0xe7bb5145 via the UR, nonce 145-185) as the
operator's scheduled buy; front = our buy at the end of launch+1, sell one block after that buy (if behind ours) else launch+20; plus a grid of
fixed holds (sell at launch+2..+20) to show no hold makes money; and the depth: the ETH of net buying behind us needed to cover the 8% tax"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
key = json.load(open(os.path.join(HERE, "keys.json")))[3]
pids = F[key]["pids"]; E = load_events(set(pids))
out = {"per_pool": [], "grid": {}}
grid = collections.defaultdict(list)
for pid in pids:
    pool = Pool(P[pid], E[pid], T, M); b0 = pool.b0
    b777 = next((x for x in pool.buys() if abs(x["eth"] - 47_770_000_000_000_000) < 10**9), None)
    B = b0 + 1
    if b777 and b777["bn"] > B: S = min(b777["bn"] + 1, b0 + 20)
    else: S = b0 + 20
    r = pool.trade(B, S)
    s_l, L_l = pool.launch_state()
    virt_eth = L_l / (s_l / Q96) / 1e18                     # virtual ETH reserve x = L / sqrtP at the launch state (after the dev buy)
    row = {"pid": pid, "b777_rel": (b777["bn"] - b0) if b777 else None, "b777_from": b777["from"] if b777 else None,
           "front_777": {k: r.get(k) for k in ("exit", "ret", "gross", "B", "S")}, "virtual_eth_reserve": round(virt_eth, 3),
           "net_buy_eth_behind_us_to_cover_two_4pct_taxes": round(virt_eth * (1 / 0.96 - 1), 4)}
    for h in range(2, 21):
        grid[h].append(pool.trade(B, b0 + h))
    out["per_pool"].append(row)
out["front_777"] = summarize([pp["front_777"] for pp in out["per_pool"]])
out["grid"] = {f"sell_at_launch+{h}": {k: v for k, v in summarize(rs).items() if k in ("n", "mean", "median", "win")} for h, rs in grid.items()}
json.dump(out, open(os.path.join(HERE, "fam4_variant.json"), "w"), indent=1)
print(json.dumps(out, indent=1)[:6000])
