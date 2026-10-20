"""decode_launch / decode_init on every launch of the candidate cores (inputs from cache/tx_launch.jsonl), not a sample."""
import pickle
from common import *
from decoders import decode_launch, decode_init
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); FAM = X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
Z = "0x" + "0" * 40
G = {"C-1 core": lambda r, k: "#cb79985d" in k and (r["quote"], r["fee"], r["hooks"]) == ("ETH", 100, Z),
     "a98b3b9e hooked core": lambda r, k: "#a98b3b9e" in k and r["hooks"] != Z and r["fee"] == 3000,
     "C-2 hooked sibling": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] != Z,
     "58d59320 via 0xeb7c0347": lambda r, k: "86b37100" in k}
want = {}
for p, k in FAM.items():
    if "@" in k: continue
    for g, f in G.items():
        if f(rows[p], k): want[rows[p]["launch_tx"]] = (g, p)
inp = {}
with open(os.path.join(CEN, "cache", "tx_launch.jsonl")) as fh:
    for line in fh:
        h = line[9:75]
        if h in want: inp[h] = json.loads(line).get("input")
for g in G:
    c = C.Counter()
    for h, (gg, p) in want.items():
        if gg != g: continue
        r = rows[p]; s = inp.get(h)
        if not s: c["no input cached"] += 1; continue
        b = bytes.fromhex(s[2:]); d = decode_launch(b); d2 = decode_init(b)
        c["n"] += 1
        c["decode_launch: pool id, sqrtP, mint liquidity from calldata"] += bool(d and d["pid"] == r["pool"] and d["sqrt_p"] == r["sqrt_p0"])
        c["decode_init: pool id and sqrtP from calldata"] += bool(d2 and d2["pid"] == r["pool"] and d2["sqrt_p"] == r["sqrt_p0"])
    print(g, dict(c))
