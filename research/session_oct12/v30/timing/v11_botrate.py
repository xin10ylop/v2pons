"""No RPC: the bot router's activity (token Transfers PoolManager -> bot router, any token: buys, plus the few pulls) around each 3.0 launch:
the share of pools with such an event in another token at each offset from L and from T. A pause-then-resume pattern would show here."""
import vc, json, collections
P = json.load(open(vc.p("v03_pools.json"))); P.sort(key=lambda o: o["L"])
ev = collections.defaultdict(set)
for l in open(vc.p("v02_botin_cache.jsonl")):
    for x in json.loads(l)["logs"]:
        if vc.topaddr(x["topics"][1]) == vc.PM: ev[int(x["blockNumber"], 16)].add(x["address"].lower())
def prof(S, ref, rng):
    out = []
    for k in rng:
        out.append(sum(1 for o in S if any(t != o["tok"] for t in ev.get(o[ref] + k, ()))) / len(S))
    return out
for name, S in (("all", P), ("08-09h", [o for o in P if vc.hh(o["t"]) in ("08h", "09h")]), ("other hours", [o for o in P if vc.hh(o["t"]) not in ("08h", "09h")])):
    print("== %s (%d pools)" % (name, len(S)))
    rL = prof(S, "L", range(-30, 81)); rT = prof(S, "T", range(-40, 31))
    print(" from L: " + " ".join("%+d:%.0f" % (k, 100 * v) for k, v in zip(range(-30, 81), rL)))
    print(" from T: " + " ".join("%+d:%.0f" % (k, 100 * v) for k, v in zip(range(-40, 31), rT)))
    # summaries by band
    def band(r, rng, a, b): v = [x for k, x in zip(rng, r) if a <= k <= b]; return 100 * sum(v) / len(v)
    print(" bands (%% of pools per block): L-30..L-1 %.1f | L..L+15 %.1f | L+16..T-1 (T-40..T-1) %.1f | T-4..T-1 %.1f | T+1..T+10 %.1f | T+11..T+30 %.1f" % (
        band(rL, range(-30, 81), -30, -1), band(rL, range(-30, 81), 0, 15), band(rT, range(-40, 31), -40, -1), band(rT, range(-40, 31), -4, -1), band(rT, range(-40, 31), 1, 10), band(rT, range(-40, 31), 11, 30)))
