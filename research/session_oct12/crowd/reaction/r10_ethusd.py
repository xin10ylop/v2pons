"""the ETH price on chain: the V3 factory's WETH/USDG pools (USDG 0x5fc5360d..., 6 decimals; getPool for each fee tier), each pool's
slot0 and liquidity; the price from the deepest one."""
from common import *
import rpc
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
def call(to, data): return rpc.call("eth_call", [{"to": to, "data": data}, "latest"])
t0, t1 = sorted([WETH, USDG])
for fee in (100, 500, 3000, 10000):
    r = call(FACT, "0x1698ee82" + t0[2:].zfill(64) + t1[2:].zfill(64) + "%064x" % fee)
    pool = "0x" + r[-40:]
    if int(pool, 16) == 0: print(fee, "no pool"); continue
    s0 = call(pool, "0x3850c7bd"); liq = int(call(pool, "0x1a686502"), 16); sp = int(s0[2:66], 16)
    p = (sp / 2 ** 96) ** 2          # token1 per token0, raw
    usd = p * 1e18 / 1e6 if t0 == WETH else 1 / p * 1e18 / 1e6
    print(f"fee {fee}: pool {pool} liquidity {liq:.3e}  ETH = {usd:,.2f} USDG")
print(rpc.STATS)
