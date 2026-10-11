"""Token price (in the quote) at frb + k relative to the price just after the first real buy, p10/p50/p90 over the pools of each group."""
import pickle
from common import *
from replay import Pool
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
Z = "0x" + "0" * 40
G = {"a98b3b9e hooked core": lambda r, k: "#a98b3b9e" in k and r["hooks"] != Z and r["fee"] == 3000,
     "C-2 hooked sibling": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] != Z,
     "C-1 core": lambda r, k: "#cb79985d" in k and (r["quote"], r["fee"], r["hooks"]) == ("ETH", 100, Z),
     "C-2 hookless core": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] == Z and r["fee"] == 500}
for g, f in G.items():
    ps = [p for p, k in FAM.items() if "@" not in k and f(rows[p], k) and rows[p]["frb"]]
    agg = C.defaultdict(list)
    for p in ps:
        r = rows[p]; P = Pool(r, E[p]); fb = r["launch_block"] + r["frb"]["off"]
        def price_at(blk):
            sp, _ = P.state_at(blk); return (2 ** 96 / sp) ** 2 if P.qs == 0 else (sp / 2 ** 96) ** 2
        p0 = price_at(fb + 1)
        for k in (2, 10, 22, 40, 62, 100, 200, 600):
            agg[k].append(price_at(fb + k) / p0)
    print(g, len(ps), " | ".join(f"+{k}: {pct(v,.1):.2f}/{pct(v,.5):.2f}/{pct(v,.9):.2f}" for k, v in agg.items()))
