"""Cluster every launch (any pair) by a coarse fingerprint; list clusters that first appear after the last 2.433 launch, and any launch with a single 2.433 trait."""
import kc, json, collections
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
LAST = 86310320; Z = "0x" + "0" * 40
def key(r):
    v = r["value"] or 0
    return (r["to"][:10] if r["to"] else "CREATE", r["sel"], r["clen"], round(v / 1e18, 4), r["fee"], r["ts"], r["hooks"][-6:], "%.3e" % r["sqrtp"], r["gas"], "ETH" if r["c0"] == Z else "TOK")
pre = collections.Counter(key(r) for r in rows if r["block"] <= LAST)
post = collections.defaultdict(list)
for r in rows:
    if r["block"] > LAST: post[key(r)].append(r)
print("launches pre %d post %d; clusters pre %d post %d" % (sum(pre.values()), sum(len(v) for v in post.values()), len(pre), len(post)))
new = sorted(((k, v) for k, v in post.items() if k not in pre), key=lambda kv: -len(kv[1]))
print("post-only clusters:", len(new), "covering", sum(len(v) for k, v in new), "launches")
for k, v in new[:40]:
    print("  %4d  first %s last %s  %s  senders %d  nonce %s  tok777 %d" % (len(v), kc.ts(v[0]["t"]), kc.ts(v[-1]["t"]), k, len(set(x["from"] for x in v)), collections.Counter(x["nonce"] for x in v).most_common(2), sum(1 for x in v if x["c1"].endswith("777"))))
# single-trait matches after stop
post_all = [r for r in rows if r["block"] > LAST]
print("\nAfter the stop, single 2.433 traits:")
print("  value within 10%% of 2.4333285: %d" % sum(1 for r in post_all if r["value"] and abs(r["value"] / kc.V2433 - 1) < .10))
for r in post_all:
    if r["value"] and abs(r["value"] / kc.V2433 - 1) < .10: print("     ", kc.ts(r["t"]), r["value"] / 1e18, r["fee"], r["ts"], r["hooks"][-6:], "%.4e" % r["sqrtp"], r["from"], r["clen"])
print("  sqrtP within 3%%: %d" % sum(1 for r in post_all if abs(r["sqrtp"] / kc.SQ2433 - 1) < .03))
print("  fee 5000/ts100 or 2500/50: %d" % sum(1 for r in post_all if (r["fee"], r["ts"]) in ((5000, 100), (2500, 50))))
print("  fee 5000 any ts: %d ; ts 100 any fee: %d" % (sum(1 for r in post_all if r["fee"] == 5000), sum(1 for r in post_all if r["ts"] == 100)))
print("  gas limit 15,000,000 to POSM by fee/ts/value:", collections.Counter((r["fee"], r["ts"], round((r["value"] or 0) / 1e18, 4)) for r in post_all if r["gas"] == 15000000).most_common(8))
print("  ETH-pair token ending 777 (not 3.0/5.0 sqrtP):", collections.Counter((round((r["value"] or 0) / 1e18, 4), r["fee"], r["ts"]) for r in post_all if r["c1"].endswith("777") and r["sqrtp"] not in (679394651928963067279918579724198, 526364174002223567019744861584709)).most_common(10))
print("  launch-tx nonce 11 to POSM, by value:", collections.Counter(round((r["value"] or 0) / 1e18, 4) for r in post_all if r["nonce"] == 11 and r["to"] == kc.POSM).most_common(10))
