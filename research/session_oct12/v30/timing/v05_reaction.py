"""Buys before T: per sender class; every pool with a non-dust buy (>= 0.00003 ETH, not the bot router, not the 2e-6 sentinel 0xe71a69f4) before T,
its pull lag and the bot's buys. Also the pull lag after T for all pools (baseline) and the outlier T pools."""
import vc, json, collections
P = json.load(open(vc.p("v03_pools.json")))
cls = collections.Counter(); cls_eth = collections.defaultdict(list); sent_offs = collections.Counter()
for o in P:
    for x in o["pre"]:
        if x["side"] != "buy": continue
        k = (x["from"] or "?")[:10]; cls[k] += 1; cls_eth[k].append(x["eth"])
        if k == vc.SENTINEL: sent_offs[x["d"]] += 1
print("buys before T by sender (top 20):")
for k, n in cls.most_common(20):
    e = cls_eth[k]; print("  %s %4d buys  eth min/med/max %.2e/%.2e/%.2e" % (k, n, min(e), vc.q(e, .5), max(e)))
print("sentinel offsets:", sorted(sent_offs.items()), " pools with sentinel:", sum(1 for o in P if any((x['from'] or '')[:10] == vc.SENTINEL for x in o['pre'])))
sells_pre = [(o["L"], x) for o in P for x in o["pre"] if x["side"] == "sell"]
print("sells before T:", len(sells_pre), collections.Counter((x["from"] or "?")[:10] for _, x in sells_pre).most_common(5))
print("\nPOOLS WITH A NON-DUST NON-BOT NON-SENTINEL BUY BEFORE T (incl. in block T ahead of the bot):")
hdr = "%-15s %9s %4s %5s %-11s %-11s %-10s %9s %5s %8s %5s %7s %s" % ("launch UTC", "L", "T-L", "buyd", "from", "to", "sel", "ETH", "pull", "pull-buy", "nbuy", "botETH", "pull-T")
print(hdr)
F = []
for o in P:
    nd = [x for x in o["pre"] if x["side"] == "buy" and x["eth"] * 1e18 >= vc.DUST and (x["from"] or "")[:10] != vc.SENTINEL]
    if not nd: continue
    x = nd[0]; F.append((o, nd))
    print("%-15s %9d %4d %5d %-11s %-11s %-10s %9.5f %5d %8d %5d %7.3f %5d %s" % (vc.ts(o["t"]), o["L"], o["d"], x["d"], x["from"][:10], x["to"][:10], x["sel"], x["eth"], o["pull"] - o["L"], o["pull"] - x["b"], o["nbuy"], o["eth_buy"], o["pull"] - o["T"],
          ("+%d more: " % (len(nd) - 1) + str([(y["d"], y["from"][:10], round(y["eth"], 5)) for y in nd[1:4]])) if len(nd) > 1 else ""))
print("\n%d pools with an early non-dust buy, the bot bought in %d; pull lag after the first early buy: %s" % (len(F), sum(1 for o, _ in F if o["T"] is not None), sorted(o["pull"] - nd[0]["b"] for o, nd in F)))
# baseline: pool life and bot buys for clean pools vs fronted pools
clean = [o for o in P if all(not (x["side"] == "buy" and x["eth"] * 1e18 >= vc.DUST and (x["from"] or "")[:10] != vc.SENTINEL) for x in o["pre"])]
for name, S in (("clean", clean), ("fronted", [o for o, _ in F])):
    if not S: continue
    pl = [o["pull"] - o["T"] for o in S]; nb = [o["nbuy"] for o in S]
    print("%-8s n %3d  pull-T p10/50/90 %s/%s/%s  bot buys p10/50/90 %s/%s/%s  bot ETH med %.2f" % (name, len(S), vc.q(pl, .1), vc.q(pl, .5), vc.q(pl, .9), vc.q(nb, .1), vc.q(nb, .5), vc.q(nb, .9), vc.q([o["eth_buy"] for o in S], .5)))
print("\nOUTLIER T (T-L > 61):")
for o in P:
    if o["d"] > 61:
        print("  %s L %d T-L %d nbuy %d pull-T %d pre: %s" % (vc.ts(o["t"]), o["L"], o["d"], o["nbuy"], o["pull"] - o["T"], [(x["d"], x["side"], (x["from"] or "")[:10], round(x["eth"], 6)) for x in o["pre"]][:8]))
json.dump([{"id": o["id"], "L": o["L"], "t": o["t"], "T": o["T"], "d": o["d"], "pull": o["pull"], "nbuy": o["nbuy"], "eth_buy": o["eth_buy"],
            "early": [{k: y[k] for k in ("d", "b", "from", "to", "sel", "eth", "tx")} for y in nd]} for o, nd in F], open(vc.p("v05_fronted.json"), "w"), indent=0)
