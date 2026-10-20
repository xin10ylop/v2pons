"""Stage 8 (does T follow a wall clock instead of an event?): block timestamps are whole seconds and ~10 blocks share one second. For each
pool of the last 2 h: T in seconds after L's timestamp; T's position inside its second (0 = the first block carrying that timestamp);
the same for L, the sentinel's dust buy and the bot's 2nd buy; and the deadline in the bot's calldata (word 6) minus T's timestamp.
A timer firing at whole seconds would put T at position 0-1 far more often than the ~1/10 a random block gets."""
import pickle, collections, os
from lib import *
os.chdir(HERE)
D = pickle.load(open("u2_parsed.pkl", "rb")); kb = KV("blk")
G = [p for p in D["pools"] if p["recent2h"] and p["T"] is not None]
def pos_in_second(bn):
    ts = kb.d[str(bn)]["ts"]; k = 0
    while str(bn - k - 1) in kb.d and kb.d[str(bn - k - 1)]["ts"] == ts: k += 1
    if str(bn - k - 1) not in kb.d: return None
    return k
def sec_len(bn):
    ts = kb.d[str(bn)]["ts"]; a = bn; b = bn
    while str(a - 1) in kb.d and kb.d[str(a - 1)]["ts"] == ts: a -= 1
    while str(b + 1) in kb.d and kb.d[str(b + 1)]["ts"] == ts: b += 1
    if str(a - 1) not in kb.d or str(b + 1) not in kb.d: return None
    return b - a + 1
secs = []; posT = []; posL = []; posS = []; posAll = []; lens = []; blocks_vs_secs = []
for p in G:
    tL = kb.d[str(p["L"])]["ts"]; tT = kb.d[str(p["Tbn"])]["ts"]; secs.append(tT - tL); blocks_vs_secs.append((tT - tL, p["T"]))
    posT.append(pos_in_second(p["Tbn"])); posL.append(pos_in_second(p["L"]))
    s = next((s for s in p["sw"] if s["who"] == "sentinel"), None)
    if s and str(s["bn"]) in kb.d: posS.append(pos_in_second(s["bn"]))
    for bn in range(p["L"] + 4, p["Tbn"] - 12): posAll.append(pos_in_second(bn)); lens.append(sec_len(bn))
c = collections.Counter
print(f"pools {len(G)} (last 2 h incl. the finder's overlap)")
print("T - L in seconds (block timestamps):", sorted(c(secs).items()))
print("by seconds, T in blocks:", {s: sorted(b for x, b in blocks_vs_secs if x == s) for s in sorted(set(secs))})
print("blocks per timestamp-second (background blocks):", sorted(c(x for x in lens if x).items()))
for lab, v in (("T (bot's first buy)", posT), ("L (launch)", posL), ("sentinel dust buy", posS), ("background blocks L+4..T-13", posAll)):
    v = [x for x in v if x is not None]; cc = c(v)
    print(f"position inside its second, {lab:28s}: n {len(v):4d} | " + " ".join(f"{k}:{100*cc[k]/len(v):.0f}%" for k in range(0, 14)))
