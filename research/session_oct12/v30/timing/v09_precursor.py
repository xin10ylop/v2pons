"""No RPC. Precursor mining on the txs of blocks L+12..T (v06): every tx gets keys (to+selector; sender class+to+selector; relations to this pool:
mentions its token / T's buyer, sent by T's buyer / its launcher, value to T's buyer). For each key: share of pools with it in block T-d (d 1..4),
its background rate per block (L+15..T-5), and the first-fire rule (arm L+a, fire at the key's first block e, our buy lands e+lat;
in time = lands in T-1..T). Keys are ranked on the discovery set (every 4th pool 05:37-11:59) and the top ones re-run on the held-out set (12:00 on)."""
import vc, json, glob, collections, sys
P = {o["id"]: o for o in json.load(open(vc.p("v03_pools.json")))}
sets = json.load(open(vc.p("v06_sets.json")))
BL = {}
for fn in sorted(glob.glob(vc.p("v06_blk_*_cache.jsonl"))):
    for l in open(fn):
        r = json.loads(l); BL[r["b"]] = r
def have(o): return all(b in BL for b in range(o["L"] + 12, o["T"] + 1))
disc = [P[i] for i in sets["disc"] if have(P[i])]; held = [P[i] for i in sets["held"] if have(P[i])]
print("pools with complete blocks: discovery %d/%d, held out %d/%d" % (len(disc), len(sets["disc"]), len(held), len(sets["held"])))
botbuyers = set(); launchers = set(o["frm"] for o in P.values()); tbuyers = set(o["t1_from"] for o in P.values())
for r in BL.values():
    for x in r["txs"]:
        if x["to"] == vc.BOT and x["s"] == "0xc1120e3d": botbuyers.add(x["f"])
botbuyers |= tbuyers
print("bot buyer wallets seen", len(botbuyers), "launchers", len(launchers))
def fclass(x, o):
    f = x["f"]
    if f == o["t1_from"]: return "Tbuyer"
    if f == o["frm"]: return "launcher"
    if f in launchers: return "launcher_other"
    if f in botbuyers: return "botbuyer"
    if f[:10] in (vc.SENTINEL, "0x7ae81404", "0xb8c879dc", "0xed165972"): return f[:10]
    return "other"
def keys(x, o):
    if x["s"] == "oracle" or x["f"].startswith("0x00000000"): return []
    to = x["to"][:10]; s = x["s"]; fc = fclass(x, o); a = x["a"]; ks = ["to:%s %s" % (to, s), "fc:%s>%s %s" % (fc, to, s), "fc:%s" % fc]
    tok = o["tok"][2:18]; tb = o["t1_from"][2:18]
    if tok in a: ks.append("rel:mentions_token")
    if tb in a: ks.append("rel:mentions_Tbuyer")
    if x["to"] == o["tok"]: ks.append("rel:to_token")
    if x["to"] == o["t1_from"]: ks.append("rel:to_Tbuyer%s" % ("_value" if x["v"] else ""))
    if x["to"] == vc.BOT: ks.append("rel:to_botrouter_any")
    if fc in ("botbuyer", "Tbuyer"): ks.append("rel:from_any_botbuyer")
    return ks
def events(o):
    """{block: set(keys)} for L+12..T, excluding the bot's T buy and anything after it in block T"""
    ev = collections.defaultdict(set)
    for b in range(o["L"] + 12, o["T"] + 1):
        for x in BL[b]["txs"]:
            if x["h"] == o["t1_tx"]: break
            for k in keys(x, o): ev[b].add(k)
    return ev
def profile(S):
    hit = collections.defaultdict(lambda: [0] * 6); bg = collections.Counter(); nbg = 0; tsame = collections.Counter()
    for o in S:
        ev = events(o); T = o["T"]
        for d in range(1, 5):
            for k in ev.get(T - d, ()): hit[k][d] += 1
        for k in set().union(*[ev.get(T - d, set()) for d in range(1, 5)]): hit[k][5] += 1
        for k in ev.get(T, ()): tsame[k] += 1
        for b in range(o["L"] + 15, T - 4):
            nbg += 1
            for k in ev.get(b, ()): bg[k] += 1
    return hit, bg, nbg, tsame
def rule(S, k, a, lat):
    ok = early = late = 0
    for o in S:
        ev = events(o)
        e = next((b for b in range(o["L"] + a, o["T"] + 1) if k in ev.get(b, ())), None)
        if e is None or e + lat > o["T"]: late += 1
        elif e + lat >= o["T"] - 1: ok += 1
        else: early += 1
    return ok, early, late
hit, bg, nbg, tsame = profile(disc)
rows = []
for k, h in hit.items():
    rate = bg[k] / nbg
    best_d = max(range(1, 5), key=lambda d: h[d])
    enr = (h[best_d] / len(disc)) / rate if rate else float("inf")
    rows.append((k, h[1:5], h[5], rate, best_d, enr))
print("\nDISCOVERY: keys present in T-4..T-1 in >= 8%% of %d pools, by enrichment of the best lead over the background per-block rate" % len(disc))
print("%-58s %-18s %6s %9s %5s %7s %7s" % ("key", "pools at d=1..4", "any1-4", "bg/blk", "bestd", "enrich", "inT<bot"))
cand = sorted([r for r in rows if r[2] >= 0.08 * len(disc)], key=lambda r: -r[5])
for k, hd, h5, rate, bd, enr in cand[:30]:
    print("%-58s %-18s %6d %9.4f %5d %7.2f %7d" % (k[:58], hd, h5, rate, bd, enr, tsame[k]))
print("\nkeys with zero background and any hit in T-4..T-1:", [(k, h5) for k, hd, h5, rate, bd, enr in rows if rate == 0 and h5 > 0][:20])
import os
cf = vc.p("v09_candidates.json")
if os.path.exists(cf): top = json.load(open(cf))["keys"]; print("\ncandidates frozen from discovery:", top)
else:
    top = []; seen = set()
    for r in cand:
        sig = (tuple(r[1]), round(r[3], 6))
        if sig in seen: continue
        seen.add(sig); top.append(r[0])
        if len(top) == 3: break
    for extra in ("rel:to_botrouter_any", "rel:from_any_botbuyer"):
        if extra not in top: top.append(extra)
    json.dump({"keys": top, "disc_pools": len(disc)}, open(cf, "w")); print("\ncandidates frozen now:", top)
for extra in ("rel:mentions_token", "rel:mentions_Tbuyer", "fc:launcher"):
    if extra not in top: top.append(extra)
print("\nFIRST-FIRE RULE (our buy lands e+lat; in time = T-1..T); discovery vs held out")
for k in top:
    for a in (15, 25):
        for lat in (1, 2):
            d = rule(disc, k, a, lat); hh = rule(held, k, a, lat)
            print("%-40s arm L+%d lat %d | disc in-time %3d early %3d none/late %3d (%.1f%% of fires) | held in-time %3d early %3d none/late %3d (%.1f%% of fires)" % (
                k[:40], a, lat, d[0], d[1], d[2], 100 * d[0] / max(1, d[0] + d[1]), hh[0], hh[1], hh[2], 100 * hh[0] / max(1, hh[0] + hh[1])))
hit2, bg2, nbg2, _ = profile(held)
print("\nHELD OUT profile of the same keys (pools at d=1..4, any, bg/blk):")
for k in top: print("  %-50s %s %d %.4f" % (k[:50], hit2[k][1:5] if k in hit2 else [0] * 4, hit2[k][5] if k in hit2 else 0, bg2[k] / max(1, nbg2)))
print("\nA-PRIORI KEYS, discovery | held out: pools with the key in block T-d (d=1..4), any of T-4..T-1, background per block L+15..T-5, in block T ahead of the bot")
for k in ("to:0x1cbaf24d 0xc1120e3d", "rel:to_botrouter_any", "rel:from_any_botbuyer", "fc:botbuyer", "fc:Tbuyer", "fc:launcher", "fc:launcher_other", "rel:mentions_token", "rel:mentions_Tbuyer",
          "rel:to_token", "rel:to_Tbuyer", "rel:to_Tbuyer_value", "fc:" + vc.SENTINEL, "fc:0x7ae81404", "fc:0xb8c879dc", "fc:0xed165972"):
    a = hit.get(k, [0] * 6); b = hit2.get(k, [0] * 6)
    print("  %-28s disc %-16s any %3d/%d bg %.4f T<bot %3d | held %-16s any %3d/%d bg %.4f" % (k, a[1:5], a[5], len(disc), bg[k] / max(1, nbg), tsame[k], b[1:5], b[5], len(held), bg2[k] / max(1, nbg2)))
