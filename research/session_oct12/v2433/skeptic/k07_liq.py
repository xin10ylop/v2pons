"""All ModifyLiquidity events after the last 2.433 launch: any positive delta equal to (or within 1% of) the 2.433 liquidity, or full range -887200..887200 at ts 100/50."""
import kc, json, collections
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
head = max(r["block"] for r in rows)
A = 86310320 - 2000
lg = kc.cached_logs("k07_ml_cache.jsonl", {"address": kc.PM, "topics": [kc.T_ML]}, A, head, step=20000)
print("ModifyLiquidity events", len(lg), "blocks", A, head)
exact = []; near = []; fr = collections.Counter()
for l in lg:
    d = l["data"]; tl, tu, dl = kc.sgn(kc.W(d, 0)), kc.sgn(kc.W(d, 1)), kc.sgn(kc.W(d, 2))
    b = int(l["blockNumber"], 16)
    if abs(dl) == kc.L2433: exact.append((b, l["topics"][1], dl, tl, tu, l["transactionHash"]))
    elif dl > 0 and abs(dl / kc.L2433 - 1) < .01: near.append((b, l["topics"][1], dl, tl, tu))
    if (tl, tu) == (-887200, 887200) and dl > 0: fr[b > 86310320] += 1
print("|delta| == 2.433 liquidity:", len(exact))
for e in exact: print("  ", e)
print("positive delta within 1%:", len(near), near[:5])
print("full-range -887200..887200 mints (pre-window part, post):", dict(fr))
