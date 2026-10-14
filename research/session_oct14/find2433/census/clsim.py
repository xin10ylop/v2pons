"""Exact-integer concentrated-liquidity swap (Uniswap v4 / V3 SwapMath + SqrtPriceMath, exact input, tick crossing over any set of positions).
zeroForOne = currency0 in (price down). fee in ppm applied on the input per step like v4/V3 computeSwapStep."""
from v4sim import sqrt_at_tick, Q96, MIN_TICK, MAX_TICK
import bisect
MAXP = 1 << 256
def divup(a, b): return -(-a // b)
def mulDivUp(a, b, c): return divup(a * b, c)
def amt0(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    num = L * Q96 * (sb - sa)
    return divup(divup(num, sb), sa) if up else (num // sb) // sa
def amt1(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    return divup(L * (sb - sa), Q96) if up else L * (sb - sa) // Q96
def next_from_in(s, L, a, zf1):
    if zf1:   # amount0 in, round up
        if a == 0: return s
        num = L * Q96
        return divup(num * s, num + a * s)
    return s + (a * Q96) // L
def step(s, st, L, rem, fee, zf1):
    """computeSwapStep for exact input rem; returns (s_next, amount_in, amount_out, fee_amount)"""
    rl = rem * (10**6 - fee) // 10**6
    ain = amt0(st, s, L, True) if zf1 else amt1(s, st, L, True)
    if rl >= ain:
        sn = st
    else:
        sn = next_from_in(s, L, rl, zf1)
    mx = st == sn
    if zf1:
        ai = ain if mx else amt0(sn, s, L, True); ao = amt1(sn, s, L, False)
    else:
        ai = ain if mx else amt1(s, sn, L, True); ao = amt0(s, sn, L, False)
    if not mx: fa = rem - ai
    else: fa = mulDivUp(ai, fee, 10**6 - fee)
    return sn, ai, ao, fa
class Pool:
    def __init__(self, sqrt, positions, fee):
        self.s = sqrt; self.fee = fee; self.net = {}
        for tl, tu, L in positions: self.add(tl, tu, L)
    def add(self, tl, tu, L):
        self.net[tl] = self.net.get(tl, 0) + L; self.net[tu] = self.net.get(tu, 0) - L
        if self.net[tl] == 0: del self.net[tl]
        if tu in self.net and self.net[tu] == 0: del self.net[tu]
    def liq(self):
        # active liquidity at current price: sum of net for ticks <= current tick (ticks sorted); price s lies in [tick, next)
        L = 0
        for t in sorted(self.net):
            if sqrt_at_tick(t) <= self.s: L += self.net[t]
            else: break
        return L
    def swap(self, amt, zf1, fee=None):
        """exact input amt; returns output amount; updates price"""
        fee = self.fee if fee is None else fee
        ticks = sorted(self.net); rem = amt; out = 0; s = self.s
        L = self.liq()
        guard = 0
        while rem > 0 and guard < 400:
            guard += 1
            if zf1:
                # next initialized tick at or below current price
                cand = [t for t in ticks if sqrt_at_tick(t) < s]
                if cand: tn = cand[-1]; st = sqrt_at_tick(tn)
                else: tn = None; st = sqrt_at_tick(MIN_TICK) + 1
            else:
                cand = [t for t in ticks if sqrt_at_tick(t) > s]
                if cand: tn = cand[0]; st = sqrt_at_tick(tn)
                else: tn = None; st = sqrt_at_tick(MAX_TICK) - 1
            if L == 0:
                if tn is None: break
                s = st
                L += (-self.net[tn] if zf1 else self.net[tn])
                if zf1: s = st  # crossing down: price sits at tick; liquidity of the range below
                continue
            sn, ai, ao, fa = step(s, st, L, rem, fee, zf1)
            rem -= ai + fa; out += ao; s = sn
            if sn == st and tn is not None:
                L += (-self.net[tn] if zf1 else self.net[tn])
                if zf1: s = st - 0  # at the tick boundary
            elif sn != st:
                break
            if tn is None: break
        self.s = s
        return out
