"""Stage 7: when does the bot decide its first buy? Word 6 of the c1120e3d calldata is a unix deadline. deadline - ts(T block) shows how long
before landing the buy was signed (1,200 s = signed in the landing second). Also T in seconds after the launch block (block timestamps,
1-s resolution), discovery vs held-out third."""
import pickle, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["line"] == "3.0" and p["T"] is not None], key=lambda p: p["L"])
kv_tx = KV("tx"); kb = KV("blk")
n = len(P); hold = set(p["pid"] for p in P[(2 * n) // 3:])
lag = collections.Counter(); secs = {"disc": [], "hold": []}; blocks = {"disc": [], "hold": []}
for p in P:
    s = next(s for s in p["sw"] if s["bot"]); inp = kv_tx.d[s["tx"]]["input"]
    dl = int(inp[10 + 64 * 6: 10 + 64 * 7], 16); bT = kb.d.get(str(p["Tbn"])); bL = kb.d.get(str(p["L"]))
    if bT: lag[dl - bT["ts"]] += 1
    g = "hold" if p["pid"] in hold else "disc"; blocks[g].append(p["T"])
    if bT and bL: secs[g].append(bT["ts"] - bL["ts"])
print("deadline - ts(T block), seconds:", sorted(lag.items()))
for g in ("disc", "hold"):
    b = blocks[g]; s = secs[g]
    print(f"{g}: n {len(b)} T blocks p10/25/50/75/90 {[pct(b, q) for q in (.1, .25, .5, .75, .9)]} min {min(b)} max {max(b)}; share within +-1 of the mode "
          f"{max(sum(1 for x in b if abs(x - m) <= 1) for m in range(15, 65)) / len(b):.2f}")
    if s: print(f"   T seconds after L (n {len(s)}): {sorted(collections.Counter(s).items())}")
