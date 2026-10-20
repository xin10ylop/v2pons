"""exact block timestamps: (1) the 5,000-block grid extended past the census to head; (2) for ~400 recent ETH curves, the create block and every
block with a buy in the first 40 blocks (to pin the surcharge schedule in seconds)."""
import json, random
from kload import *
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
g = {}
bl = list(range(85885000, head + 1, 5000)) + [head]
r = batch([("eth_getBlockByNumber", [hex(b), False]) for b in bl])
for b, x in zip(bl, r):
    if x: g[b] = int(x["timestamp"], 16)
json.dump(g, open(os.path.join(DATA, "k_tsgrid.json"), "w"))
C = load_creates(); ce = [v for v in C.values() if v["quote"] == 0 and v["bn"] > head - 1500000]
random.seed(7); S = random.sample(ce, min(400, len(ce))); sc = {s["curve"]: s for s in S}
T = load_trades(set(sc))
need = set()
for c, ev in T.items():
    need.add(sc[c]["bn"])
    for r_ in ev:
        if r_[4] == "B" and r_[0] - sc[c]["bn"] <= 40: need.add(r_[0])
need = sorted(need); print("blocks", len(need))
r = batch([("eth_getBlockByNumber", [hex(b), False]) for b in need])
ts = {b: int(x["timestamp"], 16) for b, x in zip(need, r) if x}
json.dump({"curves": list(sc), "ts": ts}, open(os.path.join(DATA, "k21_ts.json"), "w"))
print("got", len(ts), STATS)
