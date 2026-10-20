"""No RPC: per hour, the pools' life after T (pull - T), the 'short' pools (pulled < 1,000 blocks after T) vs long, the bot's buys and ETH in each."""
import vc, json, collections
P = json.load(open(vc.p("v03_pools.json")))
print("%-5s %4s | %5s %9s %9s %9s | %5s %9s %9s %9s" % ("hour", "n", "short", "pull-T p50", "buys p50", "ETH p50", "long", "pull-T p50", "buys p50", "ETH p50"))
for h in sorted(set(vc.hh(o["t"]) for o in P)) + ["all"]:
    S = [o for o in P if h == "all" or vc.hh(o["t"]) == h]
    s = [o for o in S if o["pull"] - o["T"] < 1000]; l = [o for o in S if o["pull"] - o["T"] >= 1000]
    f = lambda X, k: vc.q([k(o) for o in X], .5) if X else "-"
    print("%-5s %4d | %5d %9s %9s %9s | %5d %9s %9s %9s" % (h, len(S), len(s), f(s, lambda o: o["pull"] - o["T"]), f(s, lambda o: o["nbuy"]), ("%.2f" % f(s, lambda o: o["eth_buy"])) if s else "-",
          len(l), f(l, lambda o: o["pull"] - o["T"]), f(l, lambda o: o["nbuy"]), ("%.2f" % f(l, lambda o: o["eth_buy"])) if l else "-"))
s = [o for o in P if o["pull"] - o["T"] < 1000]
print("short pools: T-L p10/50/90 %s/%s/%s; long pools: %s/%s/%s" % (vc.q([o["d"] for o in s], .1), vc.q([o["d"] for o in s], .5), vc.q([o["d"] for o in s], .9),
      vc.q([o["d"] for o in P if o not in s], .1), vc.q([o["d"] for o in P if o not in s], .5), vc.q([o["d"] for o in P if o not in s], .9)))
print("first bot buy ETH p10/50/90: %.3f/%.3f/%.3f" % tuple(vc.q([o["t1_eth"] for o in P], x) for x in (.1, .5, .9)))
