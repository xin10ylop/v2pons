"""where the crowd's buys after the trigger land (feed buys >= 0.0002 ETH, offsets from the trigger block T), on the 46 traded
Oct 8 original-launcher launches; and which of them are the ones that pay V0's take-profit"""
import sys, os, collections, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import follow as F, exits_bt as E
data = F.gather(); G = F.measure_gas(data)
first_after = collections.Counter(); any_in = collections.Counter(); n = 0; rows = []
for p in data["orig"]:
    L = data["launch"][p["pid"]]
    ours = {t["hash"] for b in L["blocks"] for t in b["transactions"] if t["from"][2:].lower() == F.WALLET}
    c, why = E.prep(p, L, ours)
    if c is None:
        continue
    n += 1; T = c["T"]
    offs = [f["bn"] - T for f in c["feed"] if f["bn"] > T and f["value"] >= F.MIN_TRIGGER_WEI and f["bn"] - T <= 8]
    same = [f for f in c["feed"] if f["bn"] == T and f["value"] >= F.MIN_TRIGGER_WEI]
    first_after[offs[0] if offs else None] += 1
    for o in set(offs): any_in[o] += 1
    vals = [(f["bn"] - T, round(f["value"] / 1e18, 4)) for f in c["feed"] if T <= f["bn"] <= T + 6 and f["value"] >= F.MIN_TRIGGER_WEI]
    rows.append((p["block"], c["off"], c["pull"] - T if c["pull"] else None, vals))
print(f"n {n}; first real buy after the trigger, blocks after T: {sorted(first_after.items(), key=lambda x: (x[0] is None, x[0]))}")
print("launches with a real buy at T+k:", {k: any_in[k] for k in range(1, 9)})
for r in rows:
    print(f"  launch {r[0]} trig +{r[1]:3d} pull T+{r[2]}  buys T..T+6 (T+k, ETH): {r[3]}")
