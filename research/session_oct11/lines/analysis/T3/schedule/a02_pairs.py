"""Pairs and launch-side covariates of the 3.0/5.0 first bot buy T (T = offset from L in blocks).
 - pairs: consecutive 3.0/5.0 launches <= 120 blocks apart; is T2abs - T1abs (or T2 - T1) stable?
 - T against: L mod 10, the launch tx index, the launch sender nonce, the inter-launch gap, the previous pool's T, the number of pools the bot
   is serving at L (bot buys in [L-300, L)), the T-wallet's index (rank of its first appearance)."""
import pickle, collections, statistics as st
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; acts = D["acts"]
def pc(v, ps=(.1,.25,.5,.75,.9)):
    v = sorted(v); return [v[min(len(v)-1, int(p*len(v)))] for p in ps] if v else None
def corr(x, y):
    mx, my = st.mean(x), st.mean(y); sx = sum((a-mx)**2 for a in x) ** .5; sy = sum((b-my)**2 for b in y) ** .5
    return round(sum((a-mx)*(b-my) for a, b in zip(x, y)) / (sx*sy), 3) if sx and sy else None
P = sorted([p for p in pools if p["line"] in ("3.0", "5.0")], key=lambda p: p["L"])
print(f"3.0+5.0 launches {len(P)}, with T {sum(1 for p in P if p['T'] is not None)}")
gaps = [b["L"] - a["L"] for a, b in zip(P, P[1:])]
print("gap between consecutive 3.0/5.0 launches (blocks) hist <=150:", sorted(collections.Counter(g for g in gaps if g <= 150).items()))
pairs = [(a, b) for a, b in zip(P, P[1:]) if b["L"] - a["L"] <= 120 and a["T"] is not None and b["T"] is not None]
print(f"pairs <= 120 apart with both T: {len(pairs)}")
d_abs = [b["Tbn"] - a["Tbn"] for a, b in pairs]; d_off = [b["T"] - a["T"] for a, b in pairs]
print("  T2abs - T1abs p10/25/50/75/90", pc(d_abs), " T2 - T1", pc(d_off), " corr(T1, T2)", corr([a["T"] for a, b in pairs], [b["T"] for a, b in pairs]))
print("  T2abs - T1abs - (L2 - L1) = T2 - T1; |T2abs - T1abs| <= 1 in", sum(1 for x in d_abs if abs(x) <= 1), "of", len(d_abs))
print("  same buyer wallet in a pair's two T:", sum(1 for a, b in pairs if next(x["wallet"] for x in acts if x["tx"] == a["Ttx"]) == next(x["wallet"] for x in acts if x["tx"] == b["Ttx"])))
print("  pair lines:", collections.Counter((a["line"], b["line"]) for a, b in pairs))
W = [p for p in P if p["T"] is not None]
T = [p["T"] for p in W]
print("corr T vs L mod 10:", corr([p["L"] % 10 for p in W], T), " vs launch tx index:", corr([p["Lti"] for p in W], T), " vs nonce:", corr([p["lnonce"] for p in W], T))
print("T by L mod 10:", {k: pc([p["T"] for p in W if p["L"] % 10 == k], (.5,)) for k in range(10)})
prevT = [(a["T"], b["T"]) for a, b in zip(W, W[1:])]
print("corr T vs previous pool's T:", corr([x for x, y in prevT], [y for x, y in prevT]))
# load: number of bot buys in [L-300, L)
import bisect
bb = sorted(a["bn"] for a in acts if a["kind"] != "pull")
load = [bisect.bisect_left(bb, p["L"]) - bisect.bisect_left(bb, p["L"] - 300) for p in W]
print("corr T vs bot load (buys in the 300 blocks before L):", corr(load, T), " load p10/50/90", pc(load, (.1, .5, .9)))
for lo, hi in ((0, 20), (20, 30), (30, 40), (40, 100)):
    s = [p["T"] for p, l in zip(W, load) if lo <= l < hi]; print(f"   load {lo}-{hi}: n {len(s)} T {pc(s)}")
# wallet index
first = {}
for a in acts:
    first.setdefault(a["wallet"], len(first))
wi = [first[next(x["wallet"] for x in acts if x["tx"] == p["Ttx"])] for p in W]
print("corr T vs T-wallet first-appearance rank:", corr(wi, T), "distinct T wallets", len(set(wi)))
# T in a ring: the T wallets in launch order
ws = [next(x["wallet"] for x in acts if x["tx"] == p["Ttx"]) for p in W]
print("T wallets, consecutive repeats:", sum(1 for a, b in zip(ws, ws[1:]) if a == b))
