"""Every transaction in blocks T-8..T-1 of the most recent 3.0/5.0 pools against control blocks L+8..L+16 of the same pools (quiet
pre-T blocks). For each transaction feature (to, to+selector, from-class, ETH transfer to the T wallet, anything touching the bot router
or a bot wallet), the share of pools where it appears at lag k = T - block, against its per-block rate in the control blocks.
A usable precursor would appear at one lag in nearly every pool and rarely in the control."""
import pickle, json, collections
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; acts = D["acts"]
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
FB = {}
for l in open("cache/fullblocks.jsonl"): x = json.loads(l); FB[x["n"]] = x
botw = set(a["wallet"] for a in acts if a["kind"] == "buy")
launchers = set(p["lfrom"] for p in pools)
P = [p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None and p["T"] >= 26 and all(b in FB for b in range(p["Tbn"] - 8, p["Tbn"] + 1))
     and all(b in FB for b in range(p["L"] + 8, p["L"] + 17))]
Twallet = {p["token"]: next(a["wallet"] for a in acts if a["tx"] == p["Ttx"]) for p in P}
print("pools", len(P))
def feats(t, p):
    f = {f"to {t['to'][:10]}", f"to+sel {t['to'][:10]}:{t['sel']}"}
    if t["from"] in botw: f.add("from a bot buy wallet"); f.add(f"from bot wallet to {t['to'][:10]}:{t['sel']}")
    if t["from"] == Twallet[p["token"]]: f.add("from the T wallet")
    if t["to"] == Twallet[p["token"]]: f.add("to the T wallet")
    if t["to"] in botw: f.add("to a bot buy wallet")
    if t["to"] == BOT: f.add(f"to bot router sel {t['sel']}")
    if t["from"] in launchers: f.add("from a launch sender")
    if t["from"] == SENT: f.add("from the sentinel")
    if t["sel"] == "" and t["v"] > 0: f.add("plain ETH transfer")
    if p["token"][2:] in t["in"]: f.add("calldata names the pool's token")
    return f
lagpres = collections.defaultdict(collections.Counter)   # feature -> lag -> pools present
ctrl = collections.Counter(); nctrl = 0
for p in P:
    for k in range(0, 9):
        fs = set()
        for t in FB[p["Tbn"] - k]["txs"]:
            if k == 0 and t["h"] == p["Ttx"]: break      # in block T only what precedes the bot's buy
            fs |= feats(t, p)
        for f in fs: lagpres[f][k] += 1
    for b in range(p["L"] + 8, p["L"] + 17):
        nctrl += 1
        fs = set()
        for t in FB[b]["txs"]: fs |= feats(t, p)
        for f in fs: ctrl[f] += 1
rows = []
for f, c in lagpres.items():
    base = ctrl[f] / nctrl
    for k in range(0, 9):
        share = c[k] / len(P)
        if share >= 0.10 and share > 2.5 * base + 0.03: rows.append((share - base, f, k, share, base))
rows.sort(reverse=True)
print("features over-represented at a lag (share of pools at lag k vs per-block control rate):")
for d, f, k, s, b in rows[:25]: print(f"  {f:55s} lag {k}: {s:.0%} vs control {b:.0%}")
if not rows: print("  none")
print("\nmost common features at lags 1-4 (share of pools) with control rate:")
tot = collections.Counter()
for f, c in lagpres.items(): tot[f] = sum(c[k] for k in (1, 2, 3, 4))
for f, n in tot.most_common(15): print(f"  {f:55s} lags1-4 {[lagpres[f][k] for k in (1,2,3,4)]} of {len(P)} each; control {ctrl[f]/nctrl:.0%}")
for f in ("to the T wallet", "from the T wallet", "to a bot buy wallet", "from a bot buy wallet", "calldata names the pool's token", "from a launch sender", "plain ETH transfer"):
    print(f"  {f:40s} lags 0..8: {[lagpres[f][k] for k in range(9)]}  control {ctrl[f]}/{nctrl}")
print("  bot-router selectors at lags 0..8:", {f: [lagpres[f][k] for k in range(9)] for f in lagpres if f.startswith("to bot router")}, "control", {f: ctrl[f] for f in ctrl if f.startswith("to bot router")})
