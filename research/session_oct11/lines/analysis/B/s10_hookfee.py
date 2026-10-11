"""Hidden input-side hook/router fees: for the fetched buy transactions (first 12 swaps etc.) of the hooked candidate (a98b3b9e core) and
controls, the ratio of the pool's quote-in (Swap event) to the transaction's ETH value. ~1.0 = the pool got all the ETH sent."""
import pickle
from common import *
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
def shape_of(r): return (r["quote"], r["fee"], r["tick_spacing"], r["hooks"] == "0x" + "0" * 40)
groups = {"a98b3b9e core (hooked, ETH 3000/60)": lambda r: "a98b3b9e" in FAM[r["pool"]] and shape_of(r) == ("ETH", 3000, 60, False),
          "C-1 core (no hook, ETH 100/1)": lambda r: "cb79985d" in FAM[r["pool"]] and shape_of(r) == ("ETH", 100, 1, True),
          "C-2 core (no hook, ETH 500/1)": lambda r: "4e451d1a" in FAM[r["pool"]] and shape_of(r) == ("ETH", 500, 1, True)}
need = {}
for p, r in rows.items():
    for g, f in groups.items():
        if f(r):
            for e in E[p]["ev"]:
                if e[0] == "s" and e[6] < 0: need[e[12]] = (g, -e[6])
txv = {}
for n in ("tx_swap.jsonl", "tx_swap_b.jsonl"):
    with open(os.path.join(CEN, "cache", n)) as fh:
        for line in fh:
            h = line[9:75]
            if h in need:
                x = json.loads(line); txv[h] = x["value_wei"]
res = C.defaultdict(list)
for h, (g, q) in need.items():
    v = txv.get(h)
    if v: res[g].append(q / v)
for g, xs in res.items():
    print(f"{g}: buys with tx value {len(xs)}; pool ETH in / tx value p10/p50/p90 {pct(xs,.1):.4f}/{pct(xs,.5):.4f}/{pct(xs,.9):.4f}; share < 0.99: {sum(1 for x in xs if x < 0.99)/len(xs):.1%}")
