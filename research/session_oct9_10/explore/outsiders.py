import pickle, collections, sys
sys.path.insert(0, ".")
P = pickle.load(open("pools.pkl", "rb")); TX = pickle.load(open("../vbot/cache_tx.pkl", "rb"))
EXEC = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
def fam(p):
    if p.get("inlen") != 1444 or p.get("sel") != "0xac9650d8": return None
    if p["fee"] == 2500: return "v2.433"
    if p["fee"] == 10000 and round(p["value"], 3) == 5.0: return "v5.0"
    if p["fee"] == 10000 and round(p["value"], 3) == 3.0: return "v3.0"
print("tx cache", len(TX))
for F in ("v2.433", "v5.0", "v3.0"):
    rt = collections.Counter(); ok = []; cov = 0
    for p in P.values():
        if "sw" not in p or fam(p) != F: continue
        buys = collections.defaultdict(list); sells = collections.defaultdict(list)
        for x in p["sw"]:
            t = TX.get(x[7])
            if not t: continue
            cov += 1
            (buys if x[2] < 0 else sells)[t["from"]].append((x[0] - p["b0"], abs(x[2]) / 1e18, t["to"]))
        for w, bl in buys.items():
            if all(b[2] == EXEC for b in bl): continue
            route = bl[0][2][:10]; rt[(route, "sold" if w in sells else "held")] += 1
            if w in sells: ok.append((p["pid"][:10], w[:10], bl[:2], sells[w][:2]))
    print("==", F, "swaps with tx", cov, "| non-executor buyers by route and outcome:", rt.most_common(8))
    for x in ok[:4]: print("    round trip:", x)
