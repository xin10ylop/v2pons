"""Classify launches; find 2.433 by any single trait; list last ones."""
import kc, json, collections
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
rows.sort(key=lambda r: (r["block"]))
print("window", kc.ts(rows[0]["t"]), "..", kc.ts(rows[-1]["t"]), "n", len(rows))
by_val = [r for r in rows if r["value"] == kc.V2433]
by_sq = [r for r in rows if r["sqrtp"] == kc.SQ2433]
by_fee = [r for r in rows if (r["fee"], r["ts"]) in ((2500, 50), (5000, 100))]
print("value==2.4333285:", len(by_val), " sqrtP==2433:", len(by_sq), " fee/ts 2500/50|5000/100:", len(by_fee))
s = set(r["tx"] for r in by_val) ^ set(r["tx"] for r in by_sq)
print("symmetric diff value vs sqrtp:", len(s))
s2 = set(r["tx"] for r in by_val) ^ set(r["tx"] for r in by_fee)
print("symmetric diff value vs fee/ts:", len(s2), [ (r["fee"],r["ts"],r["value"],kc.ts(r["t"])) for r in rows if r["tx"] in s2][:10])
for r in by_val[-6:]:
    print(" ", kc.ts(r["t"]), r["block"], r["tx"][:12], r["from"], r["to"][:10], r["clen"], r["sel"], r["fee"], r["ts"], r["hooks"][-6:], r["nonce"], r["gas"])
last = by_val[-1]
print("LAST 2.433:", kc.ts(last["t"]), last["block"], last["tx"], last["from"], "token", last["c1"])
# fee/ts change
ch = [r for r in by_val if r["fee"] == 5000]
print("first fee 5000:", kc.ts(ch[0]["t"]), ch[0]["block"], " last fee 2500:", kc.ts([r for r in by_val if r["fee"]==2500][-1]["t"]))
# per hour
h = collections.Counter(time_h for time_h in (r["t"] // 3600 for r in by_val))
import time
for k in sorted(h): print("  ", time.strftime("%m-%d %H", time.gmtime(k*3600)), h[k])
# traits uniformity of fee-5000 era
print("distinct (clen,sel,to,hooks,gas,c0) among 2.433:", collections.Counter((r["clen"], r["sel"], r["to"], r["hooks"], r["gas"], r["c0"]) for r in by_val))
print("nonces:", collections.Counter(r["nonce"] for r in by_val))
print("token suffix:", collections.Counter(r["c1"][-4:] for r in by_val))
after = [r for r in rows if r["block"] > last["block"]]
print("launches after last 2.433:", len(after))
