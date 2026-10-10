import pickle, collections, sys
sys.path.insert(0, ".")
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/cache_tx.pkl", "rb"))
CT = pickle.load(open("../others/cache_crowdtx.pkl", "rb"))
print("vbot txs", len(TX), "crowdtx", len(CT))
def fam(p):
    if p["inlen"] != 1444 or p["sel"] != "0xac9650d8": return None
    if p["fee"] == 2500: return "v2.433"
    if p["fee"] == 10000 and round(p["value"], 3) == 5.0: return "v5.0"
    if p["fee"] == 10000 and round(p["value"], 3) == 3.0: return "v3.0"
for F in ("v2.433", "v5.0", "v3.0"):
    ps = [p for p in P.values() if "sw" in p and fam(p) == F]
    cov = [(p, sum(1 for x in p["sw"] if x[7] in TX and x[0] - p["b0"] <= 300), sum(1 for x in p["sw"] if x[0] - p["b0"] <= 300)) for p in ps]
    full = [p for p, a, b in cov if b and a == b]
    print("==", F, "pools", len(ps), "fully covered (+300)", len(full))
    roles = collections.Counter(); sellers = collections.Counter(); buyers = collections.Counter()
    wallet_pools = collections.defaultdict(set)
    for p in full:
        for x in p["sw"]:
            if x[0] - p["b0"] > 300: continue
            t = TX[x[7]]; w = t["from"]
            wallet_pools[w].add(p["pid"])
            (buyers if x[2] < 0 else sellers)[w] += 1
    nf = len(full)
    rec = {w for w, s in wallet_pools.items() if len(s) >= max(3, nf // 4)}
    print("  wallets", len(wallet_pools), "recurring (>= 1/4 of pools)", len(rec))
    for w in sorted(rec, key=lambda w: -len(wallet_pools[w]))[:8]:
        print("   ", w, "pools", len(wallet_pools[w]), "buys", buyers[w], "sells", sellers[w])
    # one-off wallets that sold
    oneoff_sellers = [w for w in sellers if len(wallet_pools[w]) < 3]
    oneoff_buyers = [w for w in buyers if len(wallet_pools[w]) < 3]
    print("  one-off buyers", len(oneoff_buyers), "one-off sellers", len(oneoff_sellers), "one-off wallets that both bought and sold", len(set(oneoff_sellers) & set(oneoff_buyers)))
    # deployer sells?
    dep = {p["from"] for p in full}
    print("  deployer swaps", sum(1 for w in wallet_pools if w in dep))
