import sys, json
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
FX = json.load(open("/home/user/v2pons/tests/data/front_launch.json"))
sp0 = int(FX["sqrt_p"]); L = FX["liq"]; fee = 2500
def nf(x): return x - (x*fee + 999_999)//1_000_000
Q96 = 1<<96
# ETH depth: virtual ETH reserve = L*Q96/sp
print("virtual ETH reserve", L*Q96/sp0/1e18)
stake = int(0.0012e18)
gas = 20_000_000*250_000
for other in [0.0, 0.002, 0.005, 0.008, 0.0108, 0.011, 0.02]:
    sp = float(sp0)
    toks = v4math.buy_out_int(int(sp), L, stake, fee)
    sp = v4math.sqrt_after_buy(sp, L, nf(stake))
    if other:
        sp = v4math.sqrt_after_buy(sp, L, nf(int(other*1e18)))
    eth = v4math.sell_out_int(int(sp), L, toks, fee)
    ret = (eth - stake - gas)/stake
    print(f"other behind ours {other:.4f} ETH -> take-profit ret {ret:+.3%}")
# with bot 0.12 after 0.011
sp = float(sp0); toks = v4math.buy_out_int(int(sp), L, stake, fee)
sp = v4math.sqrt_after_buy(sp, L, nf(stake)); sp = v4math.sqrt_after_buy(sp, L, nf(int(0.011e18))); sp = v4math.sqrt_after_buy(sp, L, nf(int(0.12e18)))
eth = v4math.sell_out_int(int(sp), L, toks, fee); print("bot 0.12 after 0.011:", (eth-stake-gas)/stake)
# price move from 0.0122 ETH ahead
s1 = v4math.sqrt_after_buy(float(sp0), L, nf(int(0.0122e18)))
print("price move from 0.0122 ETH:", (s1/sp0)**2 - 1)
