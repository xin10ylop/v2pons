"""Skeptic f2276/100 step 3: with every swap attributed (66 pools), who puts ETH in and who takes it out; do the crowd's wallets sell;
the crowd's cadence after its first buy; the money left for the pull."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
pools, TX = load_sample()
crowd_w = set(s["from"] for pl in pools for s in pl["swaps"] if s["crowd"])
print("crowd wallets", len(crowd_w))
cat_in = collections.Counter(); cat_out = collections.Counter(); cat_n = collections.Counter()
to_sel = collections.Counter()
sells_by_crowdw = collections.Counter()
for pl in pools:
    for s in pl["swaps"]:
        if s["crowd"]: c = "crowd_router"
        elif s["from"] in crowd_w: c = "crowd_wallet_other_route"
        elif s["from"] == DUST: c = "dust"
        elif s["from"] == pl["launcher"]: c = "launcher"
        else: c = "other"
        if s["buy"]: cat_in[c] += s["eth"]; cat_n[(c, "buy")] += 1
        else: cat_out[c] += s["eth"]; cat_n[(c, "sell")] += 1
        to_sel[(c, s["to"], s["sel"], "B" if s["buy"] else "S")] += 1
print("ETH in by category", {k: round(v / 1e18, 3) for k, v in cat_in.items()})
print("ETH out by category", {k: round(v / 1e18, 3) for k, v in cat_out.items()})
print("counts", dict(cat_n))
for k, v in to_sel.most_common(25): print("  ", k, v)
# per pool: crowd buys, other buys, sells, pull ETH
rows = []
for pl in pools:
    b0 = pl["b0"]; c1 = pl["crowd1"]
    crb = [s for s in pl["swaps"] if s["crowd"] and s["buy"]]
    oth_b = [s for s in pl["swaps"] if not s["crowd"] and s["buy"] and s["from"] != DUST]
    sells = [s for s in pl["swaps"] if not s["buy"]]
    end = pl["pull_bn"] or (b0 + 3000)
    r = {"pid": pl["pid"][:10], "src": pl["src"], "crowd1": (c1 - b0) if c1 else None, "pull": (pl["pull_bn"] - b0) if pl["pull_bn"] else None,
         "n_crowd": len(crb), "crowd_eth": round(sum(s["eth"] for s in crb) / 1e18, 3), "other_buy_eth": round(sum(s["eth"] for s in oth_b) / 1e18, 4),
         "n_other_buys": len(oth_b), "sell_eth": round(sum(s["eth"] for s in sells) / 1e18, 3), "n_sells": len(sells),
         "crowd_wallet_sell_eth": round(sum(s["eth"] for s in sells if s["from"] in crowd_w) / 1e18, 3),
         "net_in": round((sum(s["eth"] for s in pl["swaps"] if s["buy"]) - sum(s["eth"] for s in sells)) / 1e18, 3)}
    if c1:
        r["crowd_in_50"] = round(sum(s["eth"] for s in crb if c1 < s["bn"] <= c1 + 51) / 1e18, 3)
        r["sells_in_50"] = round(sum(s["eth"] for s in sells if c1 < s["bn"] <= c1 + 51) / 1e18, 3)
        r["crowd_blocks"] = sorted(set(s["bn"] - c1 for s in crb))[:12]
    rows.append(r)
for r in rows: print(json.dumps(r))
json.dump({"crowd_wallets": sorted(crowd_w), "rows": rows}, open(os.path.join(HERE, "a3_flows.json"), "w"), indent=1)
