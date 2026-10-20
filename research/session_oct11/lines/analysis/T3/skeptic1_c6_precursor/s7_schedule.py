"""Stage 7: does any schedule predict T to +-1 block on this slice (current regime)? The best +-1 window of T - L; T in seconds after L; T's
position inside its second; T - L against the previous pool's T - L (a running clock)."""
import pickle, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); kb = KV("blk")
P = sorted([p for p in D["pools"] if p["regime"] == "new" and p["T"] is not None], key=lambda p: p["L"])
Ts = [p["T"] for p in P]; c = collections.Counter(Ts)
best = max(range(15, 60), key=lambda x: c[x - 1] + c[x] + c[x + 1])
print(f"n {len(P)}; best +-1 window of T - L: {best - 1}..{best + 1} holds {c[best-1]+c[best]+c[best+1]} pools ({100*(c[best-1]+c[best]+c[best+1])/len(P):.0f}%)")
sec = collections.Counter(); pos = collections.Counter(); prevd = []
for i, p in enumerate(P):
    tsT = kb.d[str(p["Tbn"])]["ts"]; tsL = kb.d[str(p["L"] + 1)]["ts"]; sec[tsT - tsL] += 1
    k = 0
    while str(p["Tbn"] - k - 1) in kb.d and kb.d[str(p["Tbn"] - k - 1)]["ts"] == tsT: k += 1
    pos[min(k + 1, 12)] += 1
    if i: prevd.append(p["T"] - P[i - 1]["T"])
print("T second - L+1 second:", sorted(sec.items()))
print("T is block k of its second (k = 1 first):", sorted(pos.items()))
cd = collections.Counter(prevd); b2 = max(range(-40, 41), key=lambda x: cd[x - 1] + cd[x] + cd[x + 1])
print(f"T - previous pool's T: p10/50/90 {pct(prevd,.1)}/{pct(prevd,.5)}/{pct(prevd,.9)}; best +-1 window {b2-1}..{b2+1} holds {cd[b2-1]+cd[b2]+cd[b2+1]} of {len(prevd)}")
