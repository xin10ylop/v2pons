"""Exact-integer concentrated-liquidity swap (Uniswap v4 / V3 SwapMath + SqrtPriceMath, exact input, tick crossing over any set of positions),
with the pool's current tick tracked like v4 (a price exactly on an initialized tick after a downward cross sits at tick-1).
zeroForOne = currency0 in (price down). fee in ppm applied on the input per step like computeSwapStep."""
from v4sim import sqrt_at_tick, Q96, MIN_TICK, MAX_TICK
MIN_SQRT = 4295128739; MAX_SQRT = 1461446703485210103287273052203988822378723970342
def divup(a, b): return -(-a // b)
def amt0(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    num = L * Q96 * (sb - sa)
    return divup(divup(num, sb), sa) if up else (num // sb) // sa
def amt1(sa, sb, L, up):
    if sa > sb: sa, sb = sb, sa
    return divup(L * (sb - sa), Q96) if up else L * (sb - sa) // Q96
def next_from_in(s, L, a, zf1):
    if zf1:
        if a == 0: return s
        num = L * Q96
        return divup(num * s, num + a * s)
    return s + (a * Q96) // L
def step(s, st, L, rem, fee, zf1):
    rl = rem * (10**6 - fee) // 10**6
    ain = amt0(st, s, L, True) if zf1 else amt1(s, st, L, True)
    sn = st if rl >= ain else next_from_in(s, L, rl, zf1)
    mx = st == sn
    if zf1: ai = ain if mx else amt0(sn, s, L, True); ao = amt1(sn, s, L, False)
    else: ai = ain if mx else amt1(s, sn, L, True); ao = amt0(s, sn, L, False)
    fa = (rem - ai) if not mx else divup(ai * fee, 10**6 - fee)
    return sn, ai, ao, fa
_tc = {}
def sat(t):
    v = _tc.get(t)
    if v is None: v = _tc[t] = sqrt_at_tick(t)
    return v
def tick_at(s):
    lo, hi = MIN_TICK, MAX_TICK
    while lo < hi:
        m = (lo + hi + 1) // 2
        if sat(m) <= s: lo = m
        else: hi = m - 1
    return lo
class Pool:
    def __init__(self, sqrt, positions, fee, tick=None):
        self.s = sqrt; self.fee = fee; self.net = {}
        self.tick = tick if tick is not None else tick_at(sqrt)
        for tl, tu, L in positions: self.add(tl, tu, L)
    def add(self, tl, tu, L):
        for t, d in ((tl, L), (tu, -L)):
            self.net[t] = self.net.get(t, 0) + d
            if self.net[t] == 0: del self.net[t]
    def liq(self):
        return sum(v for t, v in self.net.items() if t <= self.tick)
    def snap(self): return (self.s, self.tick, dict(self.net))
    def restore(self, x): self.s, self.tick, self.net = x[0], x[1], dict(x[2])
    def swap(self, amt, zf1, fee=None):
        fee = self.fee if fee is None else fee
        ticks = sorted(self.net); rem = amt; out = 0; s = self.s; L = self.liq(); guard = 0
        while rem > 0 and guard < 500:
            guard += 1
            if zf1:
                cand = [t for t in ticks if t <= self.tick]
                nt = cand[-1] if cand else None; st = sat(nt) if nt is not None else MIN_SQRT + 1
            else:
                cand = [t for t in ticks if t > self.tick]
                nt = cand[0] if cand else None; st = sat(nt) if nt is not None else MAX_SQRT - 1
            sn, ai, ao, fa = step(s, st, L, rem, fee, zf1)
            rem -= ai + fa; out += ao; s = sn
            if sn == st and nt is not None:
                if zf1: L -= self.net[nt]; self.tick = nt - 1
                else: L += self.net[nt]; self.tick = nt
            else:
                self.tick = tick_at(sn)
                break
        self.s = s
        return out
