"""Exact-integer Uniswap v4 swap steps for a pool with one liquidity position (full range or a range whose upper tick sits just under the
launch tick). Mirrors v4-core SwapMath/SqrtPriceMath for exact-input swaps (fee on the input, LP fee in ppm, no protocol fee).
currency0 = native ETH, currency1 = the token. A buy is zeroForOne (sqrtP falls); a sell is oneForZero (sqrtP rises)."""
Q96 = 1 << 96
MIN_TICK, MAX_TICK = -887272, 887272

def sqrt_at_tick(tick):
    a = abs(tick)
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 0x1 else 0x100000000000000000000000000000000
    for bit, m in [(0x2, 0xfff97272373d413259a46990580e213a), (0x4, 0xfff2e50f5f656932ef12357cf3c7fdcc), (0x8, 0xffe5caca7e10e4e61c3624eaa0941cd0),
                   (0x10, 0xffcb9843d60f6159c9db58835c926644), (0x20, 0xff973b41fa98c081472e6896dfb254c0), (0x40, 0xff2ea16466c96a3843ec78b326b52861),
                   (0x80, 0xfe5dee046a99a2a811c461f1969c3053), (0x100, 0xfcbe86c7900a88aedcffc83b479aa3a4), (0x200, 0xf987a7253ac413176f2b074cf7815e54),
                   (0x400, 0xf3392b0822b70005940c7a398e4b70f3), (0x800, 0xe7159475a2c29b7443b29c7fa6e889d9), (0x1000, 0xd097f3bdfd2022b8845ad8f792aa5825),
                   (0x2000, 0xa9f746462d870fdf8a65dc1f90e061e5), (0x4000, 0x70d869a156d2a1b890bb3df62baf32f7), (0x8000, 0x31be135f97d08fd981231505542fcfa6),
                   (0x10000, 0x9aa508b5b7a84e1c677de54f3e99bc9), (0x20000, 0x5d6af8dedb81196699c329225ee604), (0x40000, 0x2216e584f5fa1ea926041bedfe98),
                   (0x80000, 0x48a170391f7dc42444e8fa2)]:
        if a & bit: r = (r * m) >> 128
    if tick > 0: r = ((1 << 256) - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)

def _divup(a, b): return -(-a // b)

class Pool:
    """state: sqrt (Q64.96), liq (active liquidity), pos = (tickLower, tickUpper, L) of the single position, fee ppm"""
    def __init__(self, sqrt, pos, fee=500):
        self.sqrt = sqrt; self.pos = pos; self.fee = fee
        self.sl, self.su = sqrt_at_tick(pos[0]), sqrt_at_tick(pos[1])
    def active(self):
        return self.pos[2] if self.sl <= self.sqrt < self.su or (self.sqrt == self.su and False) else (self.pos[2] if self.sl < self.sqrt <= self.su else 0)
    def buy(self, eth_in):
        """exact ETH in -> tokens out; moves price down"""
        rem = eth_in; out = 0
        # price above the position (concentrated pool at launch): no liquidity until su, free move
        if self.sqrt > self.su:
            self.sqrt = self.su
        L = self.pos[2]
        if self.sqrt <= self.sl: return 0
        rem_less = rem * (1_000_000 - self.fee) // 1_000_000
        # amount0 needed to reach sl
        a0max = _divup(_divup(L * Q96 * (self.sqrt - self.sl), self.sqrt), self.sl)
        if rem_less >= a0max:
            raise ValueError("buy crosses the lower bound")
        num = L * Q96
        prod = rem_less * self.sqrt
        den = num + prod
        snew = _divup(num * self.sqrt, den)          # getNextSqrtPriceFromAmount0RoundingUp (add)
        out = L * (self.sqrt - snew) // Q96          # getAmount1Delta round down
        self.sqrt = snew
        return out
    def sell(self, tok_in):
        """exact token in -> ETH out; moves price up"""
        L = self.pos[2]
        if self.sqrt < self.su and self.sqrt >= self.sl:
            rem_less = tok_in * (1_000_000 - self.fee) // 1_000_000
            snew = self.sqrt + (rem_less * Q96) // L     # getNextSqrtPriceFromAmount1RoundingDown (add)
            if snew > self.su:
                # crosses out of the range: only up to su counts
                tok_needed = _divup(L * (self.su - self.sqrt), Q96)
                eth = (L * Q96 * (self.su - self.sqrt) // self.su) // self.sqrt
                self.sqrt = self.su
                return eth
            eth = (L * Q96 * (snew - self.sqrt) // snew) // self.sqrt   # getAmount0Delta round down
            self.sqrt = snew
            return eth
        return 0
