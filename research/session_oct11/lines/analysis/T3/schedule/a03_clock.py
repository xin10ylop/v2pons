"""Wall clock: block timestamps around L and T (blocks.jsonl). T - L in seconds; is T the first block of a new second (ts(T) > ts(T-1))
against the base rate; L's position in its second; T's second relative to L's second."""
import pickle, json, collections
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]
B = {}
for l in open("blocks.jsonl"): x = json.loads(l); B[x["n"]] = x
def pc(v, ps=(.1,.25,.5,.75,.9)):
    v = sorted(v); return [v[min(len(v)-1, int(p*len(v)))] for p in ps] if v else None
for line in ("3.0", "5.0", "2.433"):
    P = [p for p in pools if p["line"] == line and p["T"] is not None and all(b in B for b in (p["L"] - 1, p["L"], p["Tbn"] - 2, p["Tbn"] - 1, p["Tbn"], p["Tbn"] + 1))]
    if not P: continue
    dts = [B[p["Tbn"]]["ts"] - B[p["L"]]["ts"] for p in P]
    first_T = sum(1 for p in P if B[p["Tbn"]]["ts"] > B[p["Tbn"] - 1]["ts"])
    first_T1 = sum(1 for p in P if B[p["Tbn"] - 1]["ts"] > B[p["Tbn"] - 2]["ts"])
    first_Tp = sum(1 for p in P if B[p["Tbn"] + 1]["ts"] > B[p["Tbn"]]["ts"])
    first_L = sum(1 for p in P if B[p["L"]]["ts"] > B[p["L"] - 1]["ts"])
    print(f"=== {line}: n {len(P)}; T - L seconds hist {sorted(collections.Counter(dts).items())}")
    print(f"   T is the first block of its second in {first_T} ({first_T/len(P):.0%}); T-1: {first_T1}; T+1: {first_Tp}; L: {first_L} (base ~10%)")
    by = collections.defaultdict(list)
    for p, d in zip(P, dts): by[d].append(p["T"])
    print("   T blocks by T-L seconds:", {k: (len(v), min(v), max(v)) for k, v in sorted(by.items())})
    # blocks per second around T
    print("   T tx index in block p10/50/90:", pc([p["Tti"] for p in P], (.1, .5, .9)), " ntx in T block p50:", pc([B[p['Tbn']]['ntx'] for p in P], (.5,)))
