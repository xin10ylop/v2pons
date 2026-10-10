import sys, json
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
FX = json.load(open("/home/user/v2pons/tests/data/front_launch.json"))
S0 = int(FX["sqrt_p"]); L = FX["liq"]; fee = 2500
def net(x): return x - (x*fee + 999_999)//1_000_000
print("pool ETH-side virtual reserve L*Q96/S0 =", L * v4math.Q96 / S0 / 1e18, "ETH")
for V in (0.04, 0.05, 0.1, 0.25):
    Vw = int(V*1e18); q0 = v4math.buy_out_int(S0, L, Vw, fee)
    # threshold of ETH ahead that makes q1 < 0.99 q0
    lo, hi = 0, int(1e18)
    while hi - lo > 10**12:
        m = (lo+hi)//2
        sp = v4math.sqrt_after_buy(S0, L, net(m)); q1 = v4math.buy_out_int(int(sp), L, Vw, fee)
        if q1 < q0*0.99: hi = m
        else: lo = m
    print(f"bot buy {V} ETH: reverts when ETH ahead >= {hi/1e18:.5f}")
