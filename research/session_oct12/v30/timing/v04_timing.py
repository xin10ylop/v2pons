"""T-L per pool and per hour: count, p10/p50/p90, best fixed +-1 and +-2 block windows (in-hour and whole-period), bot buys and ETH per pool;
plus the seconds view and the launcher-class split."""
import vc, json, collections
P = json.load(open(vc.p("v03_pools.json")))
bt = {}
def best(ds, w):
    c = collections.Counter(ds); bestc, bestk = -1, None
    for k in range(min(ds) - w, max(ds) + w + 1):
        n = sum(c[k + j] for j in range(-w, w + 1))
        if n > bestc: bestc, bestk = n, k
    return bestk, bestc
print("%-5s %4s %5s %5s %5s %5s  %-14s %-14s %9s %9s %9s %9s %s" % ("hour", "n", "min", "p10", "p50", "p90", "best+-1", "best+-2", "botbuy/p", "botETH/p", "p50 buys", "max", "lo/hi"))
hours = sorted(set(vc.hh(o["t"]) for o in P))
for h in hours + ["all"]:
    S = [o for o in P if h == "all" or vc.hh(o["t"]) == h]
    ds = [o["d"] for o in S]
    k1, c1 = best(ds, 1); k2, c2 = best(ds, 2)
    nb = [o["nbuy"] for o in S]; eb = [o["eth_buy"] for o in S]
    lohi = collections.Counter("lo" if o["nonce"] < 50 else "hi" for o in S)
    print("%-5s %4d %5d %5d %5d %5d  L+%d %3d=%4.1f%%  L+%d %3d=%4.1f%% %9.1f %9.2f %9d %9d %s/%s" % (h, len(S), min(ds), vc.q(ds, .1), vc.q(ds, .5), vc.q(ds, .9), k1, c1, 100 * c1 / len(S), k2, c2, 100 * c2 / len(S),
          sum(nb) / len(S), sum(eb) / len(S), vc.q(nb, .5), max(nb), lohi["lo"], lohi["hi"]))
ds = [o["d"] for o in P]
print("\nhistogram of T-L (all %d):" % len(P))
c = collections.Counter(ds)
for k in range(min(ds), max(ds) + 1): print("  %3d %3d %s" % (k, c[k], "#" * c[k]))
print("\nsplit by launcher class (nonce<50 'lo' fresh-wallet chain / 'hi'):")
for cl in ("lo", "hi"):
    S = [o["d"] for o in P if (o["nonce"] < 50) == (cl == "lo")]
    print("  %s n %d p10/50/90 %d/%d/%d best+-1 %s best+-2 %s" % (cl, len(S), vc.q(S, .1), vc.q(S, .5), vc.q(S, .9), best(S, 1), best(S, 2)))
# held-out fixed window: pick on the first half, test on the second half; and alternating hours
P.sort(key=lambda o: o["L"])
half = len(P) // 2
for name, tr, te in (("first half -> second half", P[:half], P[half:]), ("second half -> first half", P[half:], P[:half]),
                     ("even hours -> odd hours", [o for o in P if int(vc.hh(o["t"])[:2]) % 2 == 0], [o for o in P if int(vc.hh(o["t"])[:2]) % 2 == 1]),
                     ("odd hours -> even hours", [o for o in P if int(vc.hh(o["t"])[:2]) % 2 == 1], [o for o in P if int(vc.hh(o["t"])[:2]) % 2 == 0])):
    for w in (1, 2):
        k, cc = best([o["d"] for o in tr], w)
        hit = sum(1 for o in te if abs(o["d"] - k) <= w)
        print("held-out fixed window +-%d %-28s: train best L+%d (%d/%d = %.1f%%) -> held out %d/%d = %.1f%%" % (w, name, k, cc, len(tr), 100 * cc / len(tr), hit, len(te), 100 * hit / len(te)))
# seconds view
bts = vc.block_ts_map("v04_bt_cache.jsonl", [o["T"] for o in P])
sec = [bts[o["T"]] - o["t"] for o in P]
print("\nT-L in seconds: p10/50/90 %s/%s/%s, histogram %s" % (vc.q(sec, .1), vc.q(sec, .5), vc.q(sec, .9), sorted(collections.Counter(sec).items())))
json.dump({o["id"]: bts[o["T"]] for o in P}, open(vc.p("v04_Tts.json"), "w"))
