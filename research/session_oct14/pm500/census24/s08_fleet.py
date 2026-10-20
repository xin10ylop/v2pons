"""Step 8: the scripted buyer (the fleet routers' wallets): wallets and their reuse, the buy-size schedule and the per-pool totals,
whether and when they sell, and the fleet's ETH balance per pool up to +600 and up to the pull."""
import collections, statistics
from common import *
pools = load_pools()
wallets = collections.defaultdict(set); nonces = []; routers = collections.Counter()
sched = collections.Counter(); totals600 = collections.Counter(); per_pool = []
sold = []; held = 0; buys_all = 0
for p in pools:
    sw = p["swaps"]; T = p["T"]
    fb = [s for s in sw if s["k"] == "fleet" and s["a0"] < 0]
    fs = [s for s in sw if s["k"] == "fleet" and s["a0"] > 0]
    for s in fb + fs:
        wallets[s["f"]].add(p["pid"]); routers[s["to"]] += 1
        if s["n"] is not None: nonces.append(s["n"])
    b600 = [s for s in fb if s["o"] <= 600]; s600 = [s for s in fs if s["o"] <= 600]
    ein600 = sum(-s["a0"] for s in b600) / 1e18; eout600 = sum(s["a0"] for s in s600) / 1e18
    seq = tuple(round(-s["a0"] / 1e18, 6) for s in b600)
    sched[tuple(sorted(seq))[:6]] += 1
    totals600[round(ein600, 4)] += 1
    # each fleet buy: does the same wallet sell in this pool before the pull?
    for b in fb:
        later = [s for s in fs if s["f"] == b["f"] and (s["bn"], s["li"]) > (b["bn"], b["li"])]
        buys_all += 1
        if later:
            tok = b["a1"]; back = sum(s["a0"] for s in later); tin = sum(-s["a1"] for s in later)
            sold.append(dict(lag=later[0]["o"] - b["o"], frac=min(1, tin / tok), ret=back / -b["a0"] - 1 if tin >= 0.99 * tok else None))
        else: held += 1
    ein_all = sum(-s["a0"] for s in fb) / 1e18; eout_all = sum(s["a0"] for s in fs) / 1e18
    per_pool.append(dict(pid=p["pid"], L=p["L"], T=T, n600=len(b600), s600=len(s600), ein600=ein600, eout600=eout600, nb=len(fb), ns=len(fs),
                         ein=ein_all, eout=eout_all, pull=p.get("pull_off"), last_fleet=max([s["o"] for s in fb + fs], default=None)))
print("fleet wallets", len(wallets), "| pools per wallet p50/p90/max", sorted(len(v) for v in wallets.values())[len(wallets)//2],
      sorted(len(v) for v in wallets.values())[9*len(wallets)//10], max(len(v) for v in wallets.values()))
print("routers", routers.most_common())
ns = sorted(nonces); print("wallet nonce at the swap p10/50/90", ns[len(ns)//10], ns[len(ns)//2], ns[9*len(ns)//10])
pp = [x for x in per_pool if x["nb"]]
def q(xs, a): xs = sorted(xs); return xs[int(a * (len(xs) - 1))]
for key in ("n600", "s600", "ein600", "eout600", "nb", "ns", "ein", "eout"):
    xs = [x[key] for x in pp]; print(f"per pool {key}: p10/50/90 {q(xs,.1):.4g}/{q(xs,.5):.4g}/{q(xs,.9):.4g} min {min(xs):.4g} max {max(xs):.4g}")
print("ETH-in-by-+600 totals that repeat (value: pools):", [(k, n) for k, n in totals600.most_common(12)])
print("distinct first-6 sorted buy sizes (schedules):", len(sched), sched.most_common(6))
print(f"fleet buys {buys_all}: sold later by the same wallet {len(sold)} ({len(sold)/buys_all:.0%}), never sold before the pull {held}")
if sold:
    lg = sorted(s["lag"] for s in sold); rt = sorted(s["ret"] for s in sold if s["ret"] is not None)
    print("  sell lag after its buy p10/50/90", q(lg,.1), q(lg,.5), q(lg,.9), "| return on fully sold p10/50/90", f"{q(rt,.1):+.1%} {q(rt,.5):+.1%} {q(rt,.9):+.1%}")
lf = [x["pull"] - x["last_fleet"] for x in pp if x["pull"] is not None and x["last_fleet"] is not None]
print("pull minus the fleet's last swap: p10/50/90", q(lf,.1), q(lf,.5), q(lf,.9), "min", min(lf))
jdump(per_pool, "s08_fleet_pools.json")
