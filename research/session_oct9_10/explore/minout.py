import pickle, collections, sys
sys.path.insert(0, ".")
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/cache_tx.pkl", "rb"))
def fam(p):
    if p["inlen"] != 1444 or p["sel"] != "0xac9650d8": return None
    if p["fee"] == 2500: return "v2.433"
    if p["fee"] == 10000 and round(p["value"], 3) == 5.0: return "v5.0"
    if p["fee"] == 10000 and round(p["value"], 3) == 3.0: return "v3.0"
for F in ("v2.433", "v5.0", "v3.0"):
    kinds = collections.Counter(); ratios = []; ex = None
    for p in P.values():
        if "sw" not in p or fam(p) != F: continue
        big = [x for x in p["sw"] if -x[2] >= 0.01e18]
        if not big: continue
        x = big[0]; t = TX.get(x[7])
        if not t: continue
        kinds[(t["to"][:10], t["sel"], t["inlen"], t["value"] > 0)] += 1
        inp = t["input"]
        words = [int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16) for i in range((len(inp) - 10) // 64)]
        got = x[3]  # tokens to swapper (positive)
        cands = [w for w in words if 0 < w <= got and w > got * 0.5]
        if cands: ratios.append(max(cands) / got)
        if ex is None: ex = (t, x)
    print("==", F, kinds.most_common(5))
    if ratios:
        ratios.sort(); n = len(ratios)
        print("  first big buy: largest calldata word in (0.5..1]x tokens out, ratio p10/50/90:", ratios[n // 10], ratios[n // 2], ratios[9 * n // 10], "n", n)
    if ex: print("  example input", ex[0]["input"][:400], "tokens out", ex[1][3])
