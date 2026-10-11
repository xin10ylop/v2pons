"""Load the raw events of every C-1 row (ETH core + WETH) once -> ev.pkl; print sanity counts (event senders, liquidity events)."""
import pickle
from common import *
from load import load_events
rows = [r for r in jl(os.path.join(V, "c1_rows.jsonl"))]
ids = {r["pool"] for r in rows}
E = load_events(ids)
pickle.dump(E, open(os.path.join(V, "ev.pkl"), "wb"))
print("pools", len(ids), "with events", len(E))
core = [r for r in rows if r["quote"] == "ETH"]
snd = C.Counter(); mcount = C.Counter()
for r in core:
    o = E.get(r["pool"])
    for e in o["ev"]:
        if e[0] == "s": snd[e[5]] += 1
        else: mcount[("add" if e[8] > 0 else "pull", e[5])] += 1
print("swap event senders (core ETH):", snd.most_common(12))
print("ModifyLiquidity (core ETH):", mcount.most_common(8))
