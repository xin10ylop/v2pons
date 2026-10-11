"""Stage 7b: where T's block sits inside its wall-clock second (block timestamps have 1-s resolution, ~10 blocks a second): the number of
earlier blocks with the same timestamp. A bot firing on a whole-second timer would put T near the start of a second."""
import pickle, collections
from lib import *
E = pickle.load(open("touch.pkl", "rb")); kb = KV("blk")
for s in ("cur", "old"):
    pos = collections.Counter(); per = []
    for f in E["facts"]:
        if f["set"] != s: continue
        ts = kb.d[str(f["Tbn"])]["ts"]; k = 0
        while str(f["Tbn"] - k - 1) in kb.d and kb.d[str(f["Tbn"] - k - 1)]["ts"] == ts: k += 1
        pos[k] += 1
        n = 0
        while str(f["Tbn"] - 12 + n) in kb.d and n < 16: n += 1
    print(f"{s}: blocks before T in T's own second: {sorted(pos.items())} (uniform would be ~10% each for 0..9)")
