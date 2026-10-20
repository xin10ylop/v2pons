"""Stage 7: when the bot signs its first buy (word 6 of the c1120e3d calldata is a unix deadline; deadline - 1,200 s = signing second if the
bot uses a 20-minute deadline) against the timestamp of T's block and of the launch block; and how well a fixed offset predicts T (+-1 block)."""
import pickle, collections
from lib import *
E = pickle.load(open("touch.pkl", "rb")); facts = {f["pid"]: f for f in E["facts"]}
kb = KV("blk")
CUR0 = 85553521
P = {"cur": [p for p in pickle.load(open("parsed_mid.pkl", "rb"))["pools"] if p["L"] >= CUR0 and p["T"] is not None],
     "old": [p for p in pickle.load(open("parsed_old.pkl", "rb"))["pools"] if p["T"] is not None]}
for s, PP in P.items():
    lag = collections.Counter(); secs = collections.Counter(); Ts = []
    for p in PP:
        inp = p["Tinp"]; dl = int(inp[10 + 64 * 6: 10 + 64 * 7], 16)
        bT = kb.d.get(str(p["Tbn"])); Ts.append(p["T"])
        if bT: lag[dl - bT["ts"]] += 1
        bL = kb.d.get(str(p["L"]))
        if bT and bL: secs[bT["ts"] - bL["ts"]] += 1
    best = max(range(5, 70), key=lambda m: sum(1 for x in Ts if abs(x - m) <= 1))
    print(f"{s}: n {len(PP)}; deadline - ts(T block) seconds: {sorted(lag.items())}")
    print(f"   T blocks p10/25/50/75/90 {[pct(Ts, q) for q in (.1, .25, .5, .75, .9)]}; best fixed offset {best}: within +-1 in {sum(1 for x in Ts if abs(x - best) <= 1)} of {len(Ts)}")
    if secs: print(f"   T seconds after L (pools with L's block fetched, n {sum(secs.values())}): {sorted(secs.items())}")
