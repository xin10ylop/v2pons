"""Log-only candidates over all 491 pools (no RPC): the bot router's buys in OTHER pools (Transfers PM -> bot router, any token, 3.0 and 5.0)
as a lead to T; the background rate; the first-fire rule 'arm at L+a, fire at the first other-pool bot buy, land 1 or 2 blocks later'."""
import vc, json, collections, bisect
P = json.load(open(vc.p("v03_pools.json"))); P.sort(key=lambda o: o["L"])
ev = collections.defaultdict(set)  # block -> tokens bought by the bot
for l in open(vc.p("v02_botin_cache.jsonl")):
    for x in json.loads(l)["logs"]:
        if vc.topaddr(x["topics"][1]) == vc.PM: ev[int(x["blockNumber"], 16)].add(x["address"].lower())
blocks = sorted(ev)
lo, hi = P[0]["L"], P[-1]["T"]
nb = sum(1 for b in blocks if lo <= b <= hi); print("blocks with a bot buy: %d of %d (%.3f per block)" % (nb, hi - lo + 1, nb / (hi - lo + 1)))
gaps = [b2 - b1 for b1, b2 in zip(blocks, blocks[1:]) if lo <= b1 <= hi]
print("gap between blocks with a bot buy: p10/50/90", vc.q(gaps, .1), vc.q(gaps, .5), vc.q(gaps, .9), "top", collections.Counter(gaps).most_common(8))
def other(b, tok): return any(t != tok for t in ev.get(b, ()))
lead = collections.Counter(); bg = [0, 0]
for o in P:
    for d in range(1, 5): lead[d] += other(o["T"] - d, o["tok"])
    for b in range(o["L"] + 15, o["T"] - 4): bg[0] += other(b, o["tok"]); bg[1] += 1
print("share of pools with an other-pool bot buy in block T-d:", {d: "%.1f%%" % (100 * lead[d] / len(P)) for d in range(1, 5)}, " background per block L+15..T-5: %.1f%%" % (100 * bg[0] / bg[1]))
print("same block T, another pool, before T's buy?: n/a from logs")
# rule: arm at L+a; fire at first block e >= L+a with an other-pool bot buy; land e+lat; success if land in {T-1, T}
for a in (15, 20, 25, 30, 35, 40):
    for lat in (1, 2):
        ok = early = late = 0
        for o in P:
            e = next((b for b in range(o["L"] + a, o["T"] + 1) if other(b, o["tok"])), None)
            if e is None or e + lat > o["T"]: late += 1; continue
            if e + lat >= o["T"] - 1: ok += 1
            else: early += 1
        print("arm L+%d lat %d: in time %d, early %d, late/no fire %d -> in-time share of fires %.1f%%" % (a, lat, ok, early, late, 100 * ok / max(1, ok + early + late)))
# does T line up with other-pool bot buys more than chance? the same-block co-occurrence
same = sum(1 for o in P if other(o["T"], o["tok"])); print("other-pool bot buy in block T itself: %.1f%% of pools" % (100 * same / len(P)))
