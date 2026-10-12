"""Per bot-traded pool: family, launch time, sender nonce, first bot-buy delay (blocks), bot buys; compare before/after the stop."""
import kc, json, collections, time, statistics as S
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
lg = []
for l in open(kc.p("k03_botin_cache.jsonl")): lg += json.loads(l)["logs"]
Z = "0x" + "0" * 40
tok2l = {r["c1"]: r for r in rows if r["c0"] == Z}
buys = collections.defaultdict(list); mint = {}
for l in lg:
    tok = l["address"].lower(); b = int(l["blockNumber"], 16)
    if kc.topaddr(l["topics"][1]) == Z: mint[tok] = b
    else: buys[tok].append(b)
def fam(r):
    if r["value"] == kc.V2433: return "2.433"
    if r["sqrtp"] == 679394651928963067279918579724198: return "3.0"
    if r["sqrtp"] == 526364174002223567019744861584709: return "5.0"
    return "other"
LAST = 86310320
pools = []
for tok, r in tok2l.items():
    if r["block"] < 86100000 + 5000: continue
    bb = sorted(buys.get(tok, []))
    if not bb and tok not in mint: continue
    pools.append(dict(fam=fam(r), t=r["t"], block=r["block"], nonce=r["nonce"], frm=r["from"], d1=(bb[0] - r["block"]) if bb else None, n=len(bb), mintd=(r["block"] - mint[tok]) if tok in mint else None, tok=tok, clen=r["clen"], gas=r["gas"]))
json.dump(pools, open(kc.p("k05_pools.json"), "w"))
def q(v, p): v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else None
def row(lbl, P):
    d = [x["d1"] for x in P if x["d1"] is not None]; n = [x["n"] for x in P]
    nc = collections.Counter(x["nonce"] for x in P).most_common(4)
    md = [x["mintd"] for x in P if x["mintd"] is not None]
    print("%-28s pools %4d  firstbuy p10/p50/p90 %s/%s/%s  share d1<=16: %.2f  buys/pool med %s  launch nonce top %s  mint->launch med %s  nomint %d" % (
        lbl, len(P), q(d, .1), q(d, .5), q(d, .9), (sum(1 for x in d if x <= 16) / len(d)) if d else 0, q(n, .5), nc, q(md, .5), sum(1 for x in P if x["mintd"] is None)))
for f in ("2.433", "3.0", "5.0", "other"):
    P = [x for x in pools if x["fam"] == f]
    row(f + " before stop", [x for x in P if x["block"] <= LAST])
    row(f + " after stop", [x for x in P if x["block"] > LAST])
print()
for h in range(-4, 16):
    a = 1791763200 + h * 3600  # Oct 12 00:00 UTC
    for f, cls in (("3.0", "lo"), ("3.0", "hi"), ("5.0", "hi")):
        P = [x for x in pools if x["fam"] == f and a <= x["t"] < a + 3600 and ((x["nonce"] < 50) == (cls == "lo"))]
        row("%s nonce-%s %s" % (f, cls, time.strftime("%d %Hh", time.gmtime(a))), P)
# pools whose first bot buy is in the 2.433 window (+7..+16) after the stop
fast = [x for x in pools if x["block"] > LAST and x["d1"] is not None and x["d1"] <= 16]
print("\nafter-stop pools with first bot buy <= +16:", collections.Counter(x["fam"] for x in fast))
for x in fast[:20]: print("  ", x["fam"], kc.ts(x["t"]), x["d1"], x["n"], x["nonce"], x["frm"], x["tok"])
