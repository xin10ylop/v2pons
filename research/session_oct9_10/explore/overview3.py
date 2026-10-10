import pickle, collections, json
P = pickle.load(open("pools.pkl", "rb"))
Z = "0x" + "0" * 40
BT = json.load(open("blockts.json"))
def hr(b):
    for (b1, t1), (b2, t2) in zip(BT, BT[1:]):
        if b1 <= b <= b2: return (t1 + (b - b1) * (t2 - t1) / (b2 - b1) - 1791417600) / 3600
    return None
def key(p):
    if p["ours"]: return "OURS-" + p["ours"]
    to = p["to"] or ""
    if to.startswith("create:"): to = "create"
    return (to[:10], p["sel"], p["inlen"], p["fee"], p["ts"], round(p["value"] or 0, 3))
G = collections.defaultdict(list)
for p in P.values():
    if "sw" not in p or p["hooks"] != Z: continue
    if not any(-x[2] >= 2e14 for x in p["sw"]): continue
    G[key(p)].append(p)
for k, v in sorted(G.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 8: continue
    h = collections.Counter(int(hr(p["b0"]) // 6) for p in v)
    print(k, len(v), "per 6h slice:", [h.get(i, 0) for i in range(7)], "nonce:", sorted(collections.Counter(p["nonce"] for p in v).items())[:12])
