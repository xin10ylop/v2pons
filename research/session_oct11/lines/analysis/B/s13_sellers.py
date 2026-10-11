"""Who sells in the hooked candidate pools (sellability check from the data): per group, buys/sells from the events with their Swap
`sender` (router), and among the first 12 swaps (EOA known) the sells by wallets that also bought (round trips) vs by the launch wallet."""
import pickle
from common import *
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
Z = "0x" + "0" * 40
G = {"C-2 hooked sibling": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] != Z,
     "C-2 core (no hook)": lambda r, k: "6276cbbe#4e451d1a" in k and r["hooks"] == Z and r["fee"] == 500,
     "a98b3b9e hooked core": lambda r, k: "#a98b3b9e" in k and r["hooks"] != Z and r["fee"] == 3000,
     "C-1 core": lambda r, k: "#cb79985d" in k and r["fee"] == 100 and r["hooks"] == Z,
     "58d59320 via 0xeb7c0347": lambda r, k: "86b37100" in k}
for g, f in G.items():
    ps = [p for p, k in FAM.items() if "@" not in k and f(rows[p], k)]
    nb = ns = 0; ss = C.Counter(); pools_with_sell = 0; sell_eth = buy_eth = 0
    s12 = C.Counter()
    for p in ps:
        r = rows[p]; qs = r["quote_side"]; any_sell = False
        for e in E[p]["ev"]:
            if e[0] != "s": continue
            dq = e[6] if qs == 0 else e[7]
            if dq < 0: nb += 1
            else: ns += 1; ss[e[5][:10]] += 1; any_sell = True
        pools_with_sell += any_sell
        buyers = {s[3] for s in r["swaps12"] if s[1] == "B"}
        for s in r["swaps12"]:
            if s[1] == "S": s12["sell by launch wallet" if s[3] == r["launch"]["from"] else ("sell by a wallet that bought earlier" if s[3] in buyers else "sell by other")] += 1
    print(f"{g}: pools {len(ps)}, with any sell {pools_with_sell}, buys {nb}, sells {ns}, sell routers {ss.most_common(3)}, first-12 sells {dict(s12)}")
