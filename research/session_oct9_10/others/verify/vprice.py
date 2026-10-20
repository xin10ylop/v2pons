"""Independent paper pricer for the verifier (does not use v4math or the census's 1/sqrtP shortcut).

Replays the pool's logged swaps in order (block, logIndex) as exact-input swaps of their logged input amount on a single liquidity
range, with our buy inserted at the head of block B and our sell at the head of the landing block. Without us the replay must
reproduce every logged sqrtPriceX96 (checked: `validate`). Sells by others between our buy and our sell are re-simulated (the
census's 1/sqrtP additivity is exact only for buys).

Swap tuple: (bn, li, a0, a1, sqrtP, L, tick)   a0 < 0 = ETH paid into the pool (a buy of the token).
"""
Q96 = 1 << 96


def fee_in(x, fee):           # v4 SwapMath exact-in: amountRemainingLessFee = x * (1e6 - fee) / 1e6 (floor)
    return x * (1_000_000 - fee) // 1_000_000


def buy(sp, L, x, fee):
    """x wei ETH in (gross). returns (new sqrtP, tokens out)"""
    xn = fee_in(x, fee)
    num = L * sp; den = L + (xn * sp) // Q96          # v4 getNextSqrtPriceFromAmount0RoundingUp
    sp2 = (num + den - 1) // den
    return sp2, (L * (sp - sp2)) // Q96


def sell(sp, L, y, fee):
    """y tokens in (gross). returns (new sqrtP, ETH out)"""
    yn = fee_in(y, fee)
    sp2 = sp + (yn * Q96) // L
    return sp2, (L * (sp2 - sp) * Q96) // (sp * sp2)


def apply(sp, L, s, fee):
    a0, a1 = s[2], s[3]
    if a0 < 0: return buy(sp, L, -a0, fee)[0]
    if a1 < 0: return sell(sp, L, -a1, fee)[0]
    return sp


def validate(sw, sp0, fee, upto_bn):
    """replay without us; worst relative error of sqrtP against the logs, and whether L stayed constant"""
    if not sw: return 0.0, True
    sp = sp0 if sw[0][4] is None else None
    worst = 0.0; Ls = set()
    prev_sp = None
    for i, s in enumerate(sw):
        if s[0] > upto_bn: break
        L = s[5]; Ls.add(L)
        start = sp0 if i == 0 else sw[i - 1][4]
        got = apply(start, L, s, fee)
        worst = max(worst, abs(got - s[4]) / s[4])
    return worst, len(Ls) <= 1


def follow(sw, sp0, L0, fee, B, hold, lag, pull_bn, stake=int(0.0012e18), gas=int(4.2e12), tp=0.01):
    """our buy at the head of block B; sell sent in the block of the first buy (at or after B, up to B + hold) after which our sell
    would return >= tp net of gas, else at B + hold; lands at send + lag (head of that block). pull at or before the landing = -100%."""
    pre = [s for s in sw if s[0] < B]
    sp = pre[-1][4] if pre else sp0
    L = pre[-1][5] if pre else L0
    if L <= 0: return None
    after = [s for s in sw if s[0] >= B]
    if after and after[0][5] != L: L = after[0][5]   # liquidity changed before B without a swap: take the one the next swap saw
    sp, tok = buy(sp, L, stake, fee)
    if tok <= 0: return None
    def val(spc, Lc):
        return (sell(spc, Lc, tok, fee)[1] - stake - gas) / stake
    send = B + hold; why = "deadline"
    cur = sp; Lc = L
    for s in after:
        if s[0] > B + hold: break
        Lc = s[5]
        cur = apply(cur, Lc, s, fee)
        if s[2] < 0 and val(cur, Lc) >= tp: send = s[0]; why = "tp"; break
    lb = send + lag
    if pull_bn is not None and pull_bn <= lb: return {"ret": -1.0 - gas / stake, "why": "pulled", "send": send - B}
    cur = sp; Lc = L
    for s in after:
        if s[0] >= lb: break
        Lc = s[5]; cur = apply(cur, Lc, s, fee)
    return {"ret": val(cur, Lc), "why": why, "send": send - B}
