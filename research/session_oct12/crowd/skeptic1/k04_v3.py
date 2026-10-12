"""Skeptic 1's own Uniswap V3 pool model (exact-input swaps; Mint/Burn by liquidity), written from the V3 core contracts, independent of
the replay analyst's v3exact.py. TickMath.getSqrtRatioAtTick is the W tooling's exact port (v3dec.sqrt_at_tick); getTickAtSqrtRatio is a
binary search on it (the largest tick whose sqrt ratio is <= the price, which is the library's definition). Stepping follows
TickBitmap.nextInitializedTickWithinOneWord (stops at the 256-tick word's edge), SwapMath.computeSwapStep and SqrtPriceMath with their
rounding, and liquidityNet on a crossed initialized tick."""
import sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/W")
from v3dec import sqrt_at_tick
Q96 = 1 << 96; U256 = 1 << 256
MIN_TICK, MAX_TICK = -887272, 887272
MIN_SQRT, MAX_SQRT = 4295128739, 1461446703485210103287273052203988822378723970342


def mul_div(a, b, d): return (a * b) // d
def mul_div_up(a, b, d): return -((-(a * b)) // d)
def div_up(a, b): return -((-a) // b)


def tick_at_sqrt(sp):
    lo, hi = MIN_TICK, MAX_TICK
    while lo < hi:
        m = (lo + hi + 1) // 2
        if sqrt_at_tick(m) <= sp: lo = m
        else: hi = m - 1
    return lo


def amount0_delta(a, b, liq, up):
    if a > b: a, b = b, a
    n1, n2 = liq << 96, b - a
    return div_up(mul_div_up(n1, n2, b), a) if up else mul_div(n1, n2, b) // a


def amount1_delta(a, b, liq, up):
    if a > b: a, b = b, a
    return mul_div_up(liq, b - a, Q96) if up else mul_div(liq, b - a, Q96)


def next_sqrt_from_input(sp, liq, amt, zero_for_one):
    assert sp > 0 and liq > 0
    if zero_for_one:                                 # getNextSqrtPriceFromAmount0RoundingUp(add = true)
        if amt == 0: return sp
        n1 = liq << 96; prod = amt * sp
        if prod < U256:
            den = n1 + prod
            if den < U256: return mul_div_up(n1, sp, den)
        return div_up(n1, n1 // sp + amt)
    return sp + (amt << 96) // liq                   # getNextSqrtPriceFromAmount1RoundingDown(add = true)


def swap_step(cur, target, liq, rem, fee):
    """computeSwapStep for an exact input (rem > 0) -> (next sqrt, amount in, amount out, fee amount)"""
    zfo = cur >= target
    rem_less_fee = mul_div(rem, 10 ** 6 - fee, 10 ** 6)
    amt_in = amount0_delta(target, cur, liq, True) if zfo else amount1_delta(cur, target, liq, True)
    if rem_less_fee >= amt_in: nxt = target
    else: nxt = next_sqrt_from_input(cur, liq, rem_less_fee, zfo)
    mx = nxt == target
    if zfo:
        if not mx: amt_in = amount0_delta(nxt, cur, liq, True)
        amt_out = amount1_delta(nxt, cur, liq, False)
    else:
        if not mx: amt_in = amount1_delta(cur, nxt, liq, True)
        amt_out = amount0_delta(cur, nxt, liq, False)
    fee_amt = rem - amt_in if not mx else mul_div_up(amt_in, fee, 10 ** 6 - fee)
    return nxt, amt_in, amt_out, fee_amt


class Pool:
    def __init__(self, sqrt_p, fee, spacing=1):
        self.sp = sqrt_p; self.tick = tick_at_sqrt(sqrt_p); self.liq = 0; self.fee = fee; self.spacing = spacing
        self.ticks = {}                                # tick -> [gross, net]

    def copy(self):
        q = Pool.__new__(Pool); q.sp, q.tick, q.liq, q.fee, q.spacing = self.sp, self.tick, self.liq, self.fee, self.spacing
        q.ticks = {k: list(v) for k, v in self.ticks.items()}; return q

    def _upd(self, t, d_liq, upper):
        g = self.ticks.get(t, [0, 0]); g[0] += d_liq; g[1] += -d_liq if upper else d_liq
        assert g[0] >= 0
        if g[0] == 0: self.ticks.pop(t, None)
        else: self.ticks[t] = g

    def modify(self, lo, hi, d_liq):
        """Mint (d_liq > 0) or Burn (d_liq < 0) of a position's liquidity"""
        if d_liq == 0: return
        self._upd(lo, d_liq, False); self._upd(hi, d_liq, True)
        if lo <= self.tick < hi: self.liq += d_liq

    def _next(self, zfo):
        c = self.tick // self.spacing
        if zfo:
            ws = (c >> 8) << 8
            cands = [t // self.spacing for t in self.ticks if ws <= t // self.spacing <= c]
            return (max(cands) * self.spacing, True) if cands else (ws * self.spacing, False)
        c1 = c + 1; we = ((c1 >> 8) << 8) + 255
        cands = [t // self.spacing for t in self.ticks if c1 <= t // self.spacing <= we]
        return (min(cands) * self.spacing, True) if cands else (we * self.spacing, False)

    def swap(self, zfo, amount_in):
        """exact input swap, no price limit (the router's default limit) -> (amount in used, amount out); mutates the pool"""
        if amount_in <= 0: return 0, 0
        limit = MIN_SQRT + 1 if zfo else MAX_SQRT - 1
        rem, out = amount_in, 0
        while rem != 0 and self.sp != limit:
            start = self.sp
            tn, init = self._next(zfo)
            tn = max(MIN_TICK, min(MAX_TICK, tn))
            sn = sqrt_at_tick(tn)
            tgt = (limit if sn < limit else sn) if zfo else (limit if sn > limit else sn)
            if self.liq == 0 and sn != self.sp:          # no liquidity: the price jumps to the next tick (amounts 0)
                self.sp = tgt; a_in = a_out = f = 0
            else:
                self.sp, a_in, a_out, f = swap_step(self.sp, tgt, self.liq, rem, self.fee)
            rem -= a_in + f; out += a_out
            if self.sp == sn:
                if init:
                    net = self.ticks[tn][1]
                    self.liq += -net if zfo else net
                self.tick = tn - 1 if zfo else tn
            elif self.sp != start:
                self.tick = tick_at_sqrt(self.sp)
        return amount_in - rem, out
