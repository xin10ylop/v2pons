"""analyse_25 dump_model: the 7fde822e launcher mints 25% of each token's supply (250M) straight to 0x94dddbb5, which sold into every real buy
(>= 0.0012 ETH) in the 0x06cb3a68 class 2-18 blocks later, taking back 97.9-98.2% of the buyer's ETH (dep06_non_dust_swaps in extra.json).
This prices our front buy (0.0058 ETH at launch + 1) with that dump inserted before our sell (sell at launch + 20, after every observed dump delay),
and our buy sold BEFORE the dump (at launch + 2), exactly with v4math on the launch state of the class (L 3.2156e22 at tick 201800, fee 1%).
Writes dump_model.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common25 import *  # noqa
P = load_pools(); E = load_events(); X = STAKE; FEE = 10000
ex = json.load(open(os.path.join(HERE, "extra.json")))
rows = ex["dep06_non_dust_swaps"]
pairs = []
for i, r in enumerate(rows):
    if r["side"] == "buy" and r["eth"] >= 0.0002:
        s = next((y for y in rows[i + 1:] if y["pid"] == r["pid"] and y["side"] == "sell"), None)
        if s: pairs.append({"pid": r["pid"], "buy_off": r["off"], "buy_eth": r["eth"], "dump_off": s["off"], "delay": s["off"] - r["off"], "dumper": s["from"], "ratio": s["eth"] / r["eth"]})
pid = next(p["pid"] for p in P.values() if p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937")
p = P[pid]; pl = Pool(p, E.get(pid), {}, load_blocks_meta())
s0, L = pl.state_through(p["launch_block"])   # the launch state (the dust bot's 2e-6 at +2/+3 changes nothing material)
s0 = int(s0)
tok = v4math.buy_out_int(s0, L, X, FEE)
s1 = int(Q96 / (Q96 / s0 + net_in(X, FEE) / L))
gas = pl.gas
undumped = v4math.sell_out_int(s1, L, tok, FEE)
res = {"dump_pairs": pairs, "gas_wei": gas}
res["sell_before_dump (launch+2)"] = {"eth_out": undumped / 1e18, "ret": (undumped - X - gas) / X}
# The position is TOKEN-ONLY with the launch price at its upper edge s0 (tick 201800): the only ETH a sell can take out is the ETH buyers put
# in, i.e. a sell stops at s0 (no liquidity above it). The single-range v4math.sell_out_int does not know the edge, so sells are capped here.
def amount0(L, sa, sb):          # ETH between sqrt prices sa < sb (Q96), rounded down
    return L * (sb - sa) * Q96 // (sa * sb)
def sell_capped(s, L, tokens, fee, edge):
    net = tokens - (tokens * fee + 999_999) // 1_000_000
    s_new = min(s + net * Q96 // L, edge)
    return amount0(L, s, s_new), s_new
eth_in_pool = amount0(L, s1, s0)
res["eth_in_pool_after_our_buy"] = eth_in_pool / 1e18
chk, _ = sell_capped(s1, L, tok, FEE, s0)
res["check: capped sell with no dump vs sell_out_int"] = [chk / 1e18, undumped / 1e18]
for ratio in (0.979, 0.980, 0.982):
    target = int(ratio * X)                       # the dumper takes ratio x OUR buy (it took 97.9-98.2% of each real buyer's ETH)
    lo, hi = 0, 10 ** 30
    while hi - lo > 10 ** 9:
        m = (lo + hi) // 2
        if sell_capped(s1, L, m, FEE, s0)[0] < target: lo = m
        else: hi = m
    got, s2 = sell_capped(s1, L, hi, FEE, s0)
    ours, _ = sell_capped(s2, L, tok, FEE, s0)
    res["sell_after_dump ratio %.3f" % ratio] = {"dumper_eth_out": got / 1e18, "eth_out": ours / 1e18, "ret": (ours - X - gas) / X, "usd_trade": (ours - X - gas) / 1e18 * USD_PER_ETH}
json.dump(res, open(os.path.join(HERE, "dump_model.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
