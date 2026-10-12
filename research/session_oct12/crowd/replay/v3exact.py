"""Uniswap V3 pool arithmetic in exact integers (a port of v3-core 1.0: TickMath, SqrtPriceMath, SwapMath, the swap loop with
TickBitmap.nextInitializedTickWithinOneWord stepping, tick crossing, Mint/Burn of positions). Exact-input swaps only (the crowd's, ours and
the sells re-simulated by their input). Validated by r04_validate.py: every Swap of the r01 pools reproduced from the launch state."""
import math
Q96 = 1 << 96; U256 = 1 << 256
MIN_TICK, MAX_TICK = -887272, 887272
MIN_SQRT, MAX_SQRT = 4295128739, 1461446703485210103287273052203988822378723970342

def sqrt_at_tick(tick):
    a = abs(tick)
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 1 else 0x100000000000000000000000000000000
    for bit, m in ((0x2, 0xfff97272373d413259a46990580e213a), (0x4, 0xfff2e50f5f656932ef12357cf3c7fdcc), (0x8, 0xffe5caca7e10e4e61c3624eaa0941cd0),
                   (0x10, 0xffcb9843d60f6159c9db58835c926644), (0x20, 0xff973b41fa98c081472e6896dfb254c0), (0x40, 0xff2ea16466c96a3843ec78b326b52861),
                   (0x80, 0xfe5dee046a99a2a811c461f1969c3053), (0x100, 0xfcbe86c7900a88aedcffc83b479aa3a4), (0x200, 0xf987a7253ac413176f2b074cf7815e54),
                   (0x400, 0xf3392b0822b70005940c7a398e4b70f3), (0x800, 0xe7159475a2c29b7443b29c7fa6e889d9), (0x1000, 0xd097f3bdfd2022b8845ad8f792aa5825),
                   (0x2000, 0xa9f746462d870fdf8a65dc1f90e061e5), (0x4000, 0x70d869a156d2a1b890bb3df62baf32f7), (0x8000, 0x31be135f97d08fd981231505542fcfa6),
                   (0x10000, 0x9aa508b5b7a84e1c677de54f3e99bc9), (0x20000, 0x5d6af8dedb81196699c329225ee604), (0x40000, 0x2216e584f5fa1ea926041bedfe98),
                   (0x80000, 0x48a170391f7dc42444e8fa2)):
        if a & bit:
            r = (r * m) >> 128
    if tick > 0:
        r = (U256 - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)

_cache = {}
def sat(t):
    v = _cache.get(t)
    if v is None: v = _cache[t] = sqrt_at_tick(t)
    return v

def tick_at_sqrt(sp):
    """TickMath.getTickAtSqrtRatio: the greatest tick with sqrt_at_tick(tick) <= sp (exact via a float guess and integer checks)"""
    t = math.floor(math.log((sp / Q96) ** 2) / math.log(1.0001)) if sp > 0 else MIN_TICK
    t = max(MIN_TICK, min(MAX_TICK - 1, t))
    while t > MIN_TICK and sat(t) > sp: t -= 1
    while t < MAX_TICK - 1 and sat(t + 1) <= sp: t += 1
    return t

def mul_div(a, b, d): return (a * b) // d
def mul_div_up(a, b, d):
    q, r = divmod(a * b, d); return q + (1 if r else 0)
def div_up(a, b):
    q, r = divmod(a, b); return q + (1 if r else 0)

def amount0_delta(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    n1 = L << 96; n2 = sb - sa
    return div_up(mul_div_up(n1, n2, sb), sa) if up else mul_div(n1, n2, sb) // sa

def amount1_delta(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    return mul_div_up(L, sb - sa, Q96) if up else mul_div(L, sb - sa, Q96)

def next_sqrt_from_input(sp, L, amt, zfo):
    assert sp > 0 and L > 0
    if zfo:   # getNextSqrtPriceFromAmount0RoundingUp(add)
        if amt == 0: return sp
        n1 = L << 96; prod = amt * sp
        if prod < U256:
            den = (n1 + prod) % U256
            if den >= n1: return mul_div_up(n1, sp, den)
        return div_up(n1, n1 // sp + amt)
    q = (amt << 96) // L if amt < (1 << 160) else mul_div(amt, Q96, L)
    return sp + q

def swap_step(sc, st, L, rem, fee):
    """SwapMath.computeSwapStep, exact input (rem > 0) -> (sqrt_next, amount_in, amount_out, fee_amount)"""
    zfo = sc >= st
    less_fee = mul_div(rem, 10 ** 6 - fee, 10 ** 6)
    amt_in = amount0_delta(st, sc, L, True) if zfo else amount1_delta(sc, st, L, True)
    sn = st if less_fee >= amt_in else next_sqrt_from_input(sc, L, less_fee, zfo)
    mx = st == sn
    if zfo:
        amt_in = amt_in if mx else amount0_delta(sn, sc, L, True); out = amount1_delta(sn, sc, L, False)
    else:
        amt_in = amt_in if mx else amount1_delta(sc, sn, L, True); out = amount0_delta(sc, sn, L, False)
    feeamt = rem - amt_in if sn != st else mul_div_up(amt_in, fee, 10 ** 6 - fee)
    return sn, amt_in, out, feeamt


class Pool:
    def __init__(self, sqrt_p, fee=100, spacing=1):
        self.sp = sqrt_p; self.tick = tick_at_sqrt(sqrt_p); self.L = 0; self.fee = fee; self.ts = spacing
        self.net = {}; self.gross = {}; self.init = []   # initialized ticks (sorted)
        self.pos = {}
    def copy(self):
        q = Pool.__new__(Pool); q.__dict__.update(self.__dict__)
        q.net = dict(self.net); q.gross = dict(self.gross); q.init = list(self.init); q.pos = dict(self.pos); return q
    def _upd(self, t, dl, upper):
        import bisect
        g0 = self.gross.get(t, 0); g1 = g0 + dl
        self.gross[t] = g1; self.net[t] = self.net.get(t, 0) + (-dl if upper else dl)
        if (g0 == 0) != (g1 == 0):
            i = bisect.bisect_left(self.init, t)
            if g1 == 0: self.init.pop(i); self.net.pop(t, None); self.gross.pop(t, None)
            else: self.init.insert(i, t)
    def modify(self, owner, lo, hi, dl):
        """Mint (dl > 0) or Burn (dl < 0) of a position"""
        if dl == 0: return
        k = (owner, lo, hi); self.pos[k] = self.pos.get(k, 0) + dl
        self._upd(lo, dl, False); self._upd(hi, dl, True)
        if lo <= self.tick < hi: self.L += dl
    def _next(self, zfo):
        """TickBitmap.nextInitializedTickWithinOneWord (tick spacing ts) -> (tick, initialized)"""
        import bisect
        c = self.tick // self.ts if self.tick >= 0 or self.tick % self.ts == 0 else self.tick // self.ts   # floor division = Solidity's compress
        if zfo:
            wlo = (c >> 8) << 8                  # the word's first compressed tick
            i = bisect.bisect_right(self.init, c * self.ts) - 1
            if i >= 0 and self.init[i] >= wlo * self.ts: return self.init[i], True
            return wlo * self.ts, False
        c1 = c + 1; whi = ((c1 >> 8) << 8) + 255
        i = bisect.bisect_left(self.init, c1 * self.ts)
        if i < len(self.init) and self.init[i] <= whi * self.ts: return self.init[i], True
        return whi * self.ts, False
    def swap(self, zfo, amount, limit=None):
        """exact input `amount` of token0 (zfo) or token1 -> (amount0, amount1) as the Swap event signs them (positive = into the pool)"""
        if limit is None: limit = MIN_SQRT + 1 if zfo else MAX_SQRT - 1
        rem = amount; calc = 0
        while rem != 0 and self.sp != limit:
            s0 = self.sp
            tn, ini = self._next(zfo)
            tn = max(MIN_TICK, min(MAX_TICK, tn))
            sn_t = sat(tn)
            tgt = limit if ((sn_t < limit) if zfo else (sn_t > limit)) else sn_t
            if self.L == 0:
                self.sp = tgt; ain = aout = fa = 0
            else:
                self.sp, ain, aout, fa = swap_step(self.sp, tgt, self.L, rem, self.fee)
            rem -= ain + fa; calc -= aout
            if self.sp == sn_t:
                if ini:
                    ln = self.net.get(tn, 0)
                    if zfo: ln = -ln
                    self.L += ln
                self.tick = tn - 1 if zfo else tn
            elif self.sp != s0:
                self.tick = tick_at_sqrt(self.sp)
        a_in = amount - rem
        return (a_in, calc) if zfo else (calc, a_in)
