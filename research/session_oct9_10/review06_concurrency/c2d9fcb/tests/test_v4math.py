"""v4math checks: the integer pricing against exact rational arithmetic (the float versions are for scoring and are checked to
1e-6), and the round trip's sign. Plain script: python3 tests/test_v4math.py"""
import os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import v4math

SQRT_P = 1292187213925453985058262482146976          # a real initial sqrtPriceX96 from one of the operator's pools
LIQ = 61_310_000_000_000_000_000_000                 # about 6.1e22, a real initial liquidity
Q = F(1 << 96)


def exact_buy(sqrt_p, liq, x):
    s = F(sqrt_p) / Q; s2 = 1 / (1 / s + F(x) / liq); return liq * (s - s2)


def exact_sell(sqrt_p, liq, t):
    s = F(sqrt_p) / Q; s2 = s + F(t) / liq; return liq * (1 / s - 1 / s2)


def test_integer_buy_is_exact_rounded_down():
    for eth in (10 ** 15, 10 ** 16, 10 ** 17):
        for fee in (200, 1134, 20000):
            x = eth - (eth * fee + 999_999) // 1_000_000
            e = exact_buy(SQRT_P, LIQ, x); i = v4math.buy_out_int(SQRT_P, LIQ, eth, fee); f = v4math.buy_out(SQRT_P, LIQ, x)
            assert 0 <= (e - i) <= max(2, e * 1e-15), (eth, fee, float(e), i)   # rounded down, by a fraction of a token unit
            assert abs(F(f) - e) / e < 1e-6


def test_integer_sell_is_exact_rounded_down():
    for tok in (10 ** 20, 10 ** 22, 10 ** 23):
        for fee in (200, 1134, 20000):
            x = tok - (tok * fee + 999_999) // 1_000_000
            e = exact_sell(SQRT_P, LIQ, x); i = v4math.sell_out_int(SQRT_P, LIQ, tok, fee); f = v4math.sell_out(SQRT_P, LIQ, x)
            assert 0 <= (e - i) <= max(1, e * 1e-15), (tok, fee, float(e), i)   # rounded down, by under a wei
            assert abs(F(f) - e) / e < 1e-6


def test_round_trip_loses_only_the_fees():
    eth = 10 ** 16; fee = 1134
    tok = v4math.buy_out_int(SQRT_P, LIQ, eth, fee)
    sp2 = v4math.sqrt_after_buy(SQRT_P, LIQ, eth - (eth * fee + 999_999) // 1_000_000)
    back = v4math.sell_out_int(int(sp2), LIQ, tok, fee)
    assert 0 < (eth - back) / eth < 2.5 * fee / 1e6 + 1e-6      # two fees plus our own tiny impact


def test_active_liquidity_picks_the_range_below_tick0():
    adds = [(-887200, 194000, 5), (194000, 300000, 7), (-887200, 100000, 11)]
    assert v4math.active_liquidity(194000, adds) == 5
    assert v4math.active_liquidity(150000, adds) == 5
    assert v4math.active_liquidity(50000, adds) == 16


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
