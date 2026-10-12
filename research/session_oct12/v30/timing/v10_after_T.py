"""Non-dust non-bot buys AFTER T (the reaction after T): sender, ETH, pull lag, the bot's buys after it; and the same-block front wallet 0xed165972:
every token it received in the window vs the bot's buy blocks in that token."""
import vc, json, collections
R = vc.R
P = json.load(open(vc.p("v03_pools.json"))); head = json.load(open(vc.p("v02_meta.json")))["head"]; meta = json.load(open(vc.p("v01_meta.json")))
botin = collections.defaultdict(list)
for l in vc.lines("v02_botin_cache.jsonl"):
    for x in json.loads(l)["logs"]:
        if vc.topaddr(x["topics"][1]) == vc.PM: botin[x["address"].lower()].append((int(x["blockNumber"], 16), int(x["logIndex"], 16), x["transactionHash"]))
sw = {}
for l in vc.lines("v02_swaps_cache.jsonl"):
    r = json.loads(l); sw[r["id"]] = r
cand = []
for o in P:
    bh = set(h for _, _, h in botin[o["tok"]])
    for x in sw[o["id"]]["logs"]:
        if x["b"] > o["T"] and x["tx"] not in bh and x["a0"] < 0 and -x["a0"] >= vc.DUST: cand.append((o, x))
tx = vc.txs("v10_tx_cache.jsonl", [x["tx"] for _, x in cand])
print("non-dust non-bot buys after T: %d in %d pools" % (len(cand), len(set(o["id"] for o, _ in cand))))
first = {}
for o, x in cand:
    if o["id"] not in first: first[o["id"]] = (o, x)
lags = []; bysender = collections.Counter(); rows = []
for o, x in first.values():
    t = tx[x["tx"]]; bb = [b for b, _, _ in botin[o["tok"]] if b > x["b"]]
    lag = o["pull"] - x["b"]; lags.append(lag); bysender[t["from"][:10]] += 1
    rows.append((vc.ts(o["t"]), o["L"], o["d"], x["b"] - o["L"], t["from"][:10], t["to"][:10], round(-x["a0"] / 1e18, 6), lag, o["pull"] - o["T"], len(bb)))
rows.sort()
print("%-15s %9s %4s %6s %-11s %-11s %9s %8s %7s %s" % ("launch", "L", "T-L", "buy d", "from", "to", "ETH", "pull-buy", "pull-T", "bot buys after it"))
for r in rows: print("%-15s %9d %4d %6d %-11s %-11s %9.6f %8d %7d %d" % r)
print("pull lag after the first post-T stranger buy p10/50/90 %s/%s/%s; senders %s" % (vc.q(lags, .1), vc.q(lags, .5), vc.q(lags, .9), bysender.most_common(8)))
clean = [o["pull"] - o["T"] for o in P if o["id"] not in first and not any(y["eth"] * 1e18 >= vc.DUST and (y["from"] or "")[:10] != vc.SENTINEL and y["side"] == "buy" for y in o["pre"])]
print("pools with no non-dust stranger buy at all: %d, pull-T p10/50/90 %s/%s/%s, min %s" % (len(clean), vc.q(clean, .1), vc.q(clean, .5), vc.q(clean, .9), min(clean)))
# the same-block front wallet
ED = "0xed165972d2ea6dbf719a9fc6f234566090c79314"
inl = vc.cached_logs("v10_ed_in_cache.jsonl", {"topics": [vc.T_TR, None, "0x" + "0" * 24 + ED[2:]]}, meta["start"], head, step=100000)
outl = vc.cached_logs("v10_ed_out_cache.jsonl", {"topics": [vc.T_TR, "0x" + "0" * 24 + ED[2:]]}, meta["start"], head, step=100000)
print("\n0xed165972: token transfers in %d, out %d; nonce now %s, balance %.5f ETH" % (len(inl), len(outl), int(R.call("eth_getTransactionCount", [ED, "latest"]), 16), int(R.call("eth_getBalance", [ED, "latest"]), 16) / 1e18))
tok2pool = {o["tok"]: o for o in P}
for l in inl:
    tok = l["address"].lower(); b = int(l["blockNumber"], 16); li = int(l["logIndex"], 16)
    o = tok2pool.get(tok)
    bb = sorted(botin.get(tok, []))
    same = [(bl, bli) for bl, bli, _ in bb if bl == b]
    near = [bl - b for bl, _, _ in bb if -5 <= bl - b <= 5]
    print("  block %d %s token %s %s from %s; bot buys in this token in the same block: %s, within +-5: %s" % (b, vc.ts(json.load(open(vc.p("v04_Tts.json"))).get(o["id"], 0)) if o else "", tok[:10],
          ("3.0 pool L+%d (T-L %d)" % (b - o["L"], o["d"])) if o else "not a 3.0 pool", vc.topaddr(l["topics"][1])[:10], [(s[0], s[1], li) for s in same], near))
