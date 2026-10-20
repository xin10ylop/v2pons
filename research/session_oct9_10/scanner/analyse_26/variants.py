"""analyse_26 variants on F4a / F4b (and F3 operator A for comparison): ride to a fixed block, sell after the n-th real buy, longer follow holds.
Same pricer and anchor as analyse.py (imports it as a module, which re-runs nothing heavy: analyse.py's top level is guarded below by reuse)."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common26 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
F4 = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
G = {"F4a": [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and P[x]["hooks_zero"]],
     "F4b": [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and not P[x]["hooks_zero"]],
     "F3": [p["pid"] for p in P.values() if p["launch_to"] == OPA and p["selector"] == "2fcb9108"]}
E = load_events(set(x for v in G.values() for x in v))
PL = {x: Pool(P[x], E.get(x), T, M) for v in G.values() for x in v}
def real_buys(pl, after=None):
    return [x for x in pl.buys() if x["eth"] >= MIN_REAL and x["from"] not in DUST_WALLETS and (after is None or x["bn"] > after)]
out = {}
for g, pids in G.items():
    pls = [PL[x] for x in pids]; R = {}
    for K in (20, 50, 100, 150, 200, 300, 500, 1000, 2000):
        R["ride buy live+1 sell live+%d" % K] = summarize([pl.trade(live_block(pl) + 1, live_block(pl) + K) for pl in pls])
    for n in (1, 2, 3, 5, 10, 20, 40):
        rs = []
        for pl in pls:
            lb = live_block(pl); B = lb + 1; rb = real_buys(pl, B)
            S = rb[n - 1]["bn"] + 1 if len(rb) >= n else lb + 3000
            rs.append(pl.trade(B, min(S, lb + 3000)))
        R["front buy live+1 sell 1 block after the %d-th real buy (deadline live+3000)" % n] = summarize(rs)
    for hold in (4, 10, 20, 40, 100):
        rs = []
        for pl in pls:
            rb = real_buys(pl)
            if not rb: continue
            B = rb[0]["bn"] + 1; nxt = next((x for x in rb if x["bn"] > B), None)
            S = nxt["bn"] + 1 if (nxt and nxt["bn"] + 1 <= B + hold) else B + hold
            rs.append(pl.trade(B, S))
        R["follow hold %d" % hold] = summarize(rs)
    # buy right after the first real buy, ride N blocks
    for K in (50, 100, 200, 500):
        rs = []
        for pl in pls:
            rb = real_buys(pl)
            if not rb: continue
            B = rb[0]["bn"] + 1; rs.append(pl.trade(B, B + K))
        R["follow-ride buy 1 block after the first real buy, sell %d blocks later" % K] = summarize(rs)
    out[g] = R
    print("=" * 100); print(g, len(pls))
    for k, v in R.items(): print("  %-80s %s" % (k, fmt_rule(v)))
# the crowd's real-buy rhythm in F4a/F4b: real buys per 100-block bin after live, the ETH, and the pull
for g in ("F4a", "F4b"):
    pls = [PL[x] for x in G[g]]; bins = collections.Counter(); eth = collections.Counter()
    for pl in pls:
        lb = live_block(pl)
        for x in real_buys(pl):
            bins[(x["bn"] - lb) // 100] += 1; eth[(x["bn"] - lb) // 100] += x["eth"] / 1e18
    print(g, "real buys per 100-block bin after live (count, ETH, per pool):", [(b * 100, bins[b], round(eth[b] / len(pls), 3)) for b in sorted(bins)][:30])
    out[g + "_rhythm"] = [(b * 100, bins[b], round(eth[b] / len(pls), 4)) for b in sorted(bins)]
json.dump(out, open(os.path.join(HERE, "variants.json"), "w"), indent=1, default=str)
