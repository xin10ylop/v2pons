"""v2.433 census: buys by anyone other than the volume bot, the deployer and the launch dust trio BEFORE the bot's first buy; what followed
(the bot's first buy, the pull). Also the trio's buys: pull within 15 blocks of them when they come before the first bot buy."""
import pickle, collections
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb")); TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
BOTW = {t["from"] for t in TX.values() if t["to"] == ROUTER}
TRIO = {"0xe71a69f434a719cd5afa411568b69716aab3b84a", "0xf6e55480c5939da146092301e388654879c6e6fb", "0xb002e8a04b2822d8f2890b022ddea3d25f9c3df8"}
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
rows = []; trio_pre = collections.Counter()
for p in fam:
    neg = [m for m in p["mls"] if m[4] < 0]; pull = (neg[0][0] - p["b0"]) if neg else None
    fb = None; pre = []
    for x in p["sw"]:
        t = TX.get(x[7])
        if t is None: continue
        bot = t["to"] == ROUTER or t["from"] in BOTW
        if bot and x[2] < 0: fb = x[0] - p["b0"]; break
        if x[2] < 0: pre.append((x[0] - p["b0"], -x[2] / 1e18, t["from"], t["to"]))
    for r, e, w, to in pre:
        if w in TRIO: trio_pre[(w[:8], pull is not None and pull - r <= 15)] += 1
        elif w != p["from"]: rows.append((p["pid"][:10], r, e, w[:10], to[:10], "first bot buy", fb, "pull", pull))
print("non-trio outsider buys before the bot's first buy:", len(rows))
for x in rows: print("  ", x)
print("trio buys before the first bot buy, (wallet, pulled within 15):", sorted(trio_pre.items()))
