"""what size of scheduled buy (landing after our 0.0058 ETH at the launch state) would make the front trade break even after two fees and gas,
for the launch states of the assigned families (pure arithmetic, v4math)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common18 import *
st_ = {"imortal 7fde822e (fee 1%, tick0 201800)": (None, 10000, "0x2dad39da7b"), "openlaunch 833 (fee 3%, tick0 184000)": (None, 30000, "0xfb1159ce99"),
       "openlaunch 833 (fee 3%, tick0 193200)": (None, 30000, "0x6aa71b9438")}
P = load_pools(); out = {}
for name, (_, fee, pre) in st_.items():
    p = next(v for k, v in P.items() if k.startswith(pre)); s0, L = p["sqrt_p0"], p["liq_launch"]; X = STAKE; gas = 2 * 104_000 * 20_000_000
    tok = v4math.buy_out_int(s0, L, X, fee); s1 = s_after_buy_int(s0, L, X, fee)
    def ret(Y):
        s2 = s_after_buy_int(s1, L, Y, fee); return (v4math.sell_out_int(s2, L, tok, fee) - X - gas) / X
    lo, hi = 0, int(1000e18)
    while hi - lo > int(1e12):
        m = (lo + hi) // 2
        if ret(m) >= 0: hi = m
        else: lo = m
    out[name] = {"breakeven_buy_eth": hi / 1e18, "ret_if_0.17": ret(int(0.17e18)), "ret_if_1.0": ret(int(1e18)), "eth_depth_L_over_s": L * Q96 / s0 / 1e18}
    print(name, out[name])
json.dump(out, open(os.path.join(HERE, "breakeven.json"), "w"), indent=1)
