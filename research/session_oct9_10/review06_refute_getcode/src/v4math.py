"""Exact pricing of a swap on a Uniswap v4 pool with one active liquidity range (the operator's pools: one full-depth position
whose upper tick is the initial tick, so a buy moves the price down into it). Validated against 33,769 real buys and 26,720 real
sells on the operator's pools (report 24.54: median relative error 6e-15 on buys, 2e-5 on sells; the few 1e-3 cases are pools
with a second range).

Conventions: currency0 = native ETH (address 0), currency1 = the token; sqrtP is sqrtPriceX96 (Q64.96); L is the active
liquidity; amounts in wei / raw token units. The float versions are for scoring; the integer versions reproduce the PoolManager's
arithmetic closely enough to set a buy's minOut (rounded down a little further by the engine's slip).
"""
Q96 = 1 << 96


def buy_out(sqrt_p, liq, eth_in_after_fee):
    """tokens out for `eth_in_after_fee` wei of ETH (currency0 in): 1/s' = 1/s + x/L; out = L (s - s')"""
    s = sqrt_p / Q96
    if liq <= 0 or s <= 0 or eth_in_after_fee <= 0:
        return 0.0
    s2 = 1.0 / (1.0 / s + eth_in_after_fee / liq)
    return liq * (s - s2)


def sell_out(sqrt_p, liq, tokens_in_after_fee):
    """ETH out (before the fee) for tokens in (currency1 in): s' = s + t/L; out = L (1/s - 1/s')"""
    s = sqrt_p / Q96
    if liq <= 0 or s <= 0 or tokens_in_after_fee <= 0:
        return 0.0
    s2 = s + tokens_in_after_fee / liq
    return liq * (1.0 / s - 1.0 / s2)


def sqrt_after_buy(sqrt_p, liq, eth_in_after_fee):
    """the pool's sqrtPriceX96 after a buy of `eth_in_after_fee` wei"""
    s = sqrt_p / Q96
    return (1.0 / (1.0 / s + eth_in_after_fee / liq)) * Q96


def buy_out_int(sqrt_p, liq, eth_in, fee_ppm):
    """integer version of buy_out with the fee taken on the input (fee in parts per million), rounded down as the pool rounds
    its output: the PoolManager computes the new sqrtP = L * sqrtP / (L + x * sqrtP / Q96) rounded up, and the token output
    L * (sqrtP - sqrtP') / Q96 rounded down"""
    x = eth_in - (eth_in * fee_ppm + 999_999) // 1_000_000
    num = liq * sqrt_p
    den = liq + (x * sqrt_p) // Q96
    sqrt_new = (num + den - 1) // den                      # round up: the price moves a little less, the output a little less
    return (liq * (sqrt_p - sqrt_new)) // Q96


def sell_out_int(sqrt_p, liq, tokens_in, fee_ppm):
    """integer version of sell_out with the fee on the input: new sqrtP = sqrtP + x * Q96 / L (rounded down), ETH out =
    L * Q96 * (1/sqrtP - 1/sqrtP') = L * (sqrtP' - sqrtP) * Q96 / (sqrtP * sqrtP') rounded down"""
    x = tokens_in - (tokens_in * fee_ppm + 999_999) // 1_000_000
    sqrt_new = sqrt_p + (x * Q96) // liq
    return (liq * (sqrt_new - sqrt_p) * Q96) // (sqrt_p * sqrt_new)


def active_liquidity(tick0, adds):
    """the liquidity of the ranges a buy enters first: ranges with tickLower < tick0 <= tickUpper; adds = [(tickLower, tickUpper,
    liquidityDelta)] from the pool's ModifyLiquidity events"""
    return sum(d for lo, hi, d in adds if d > 0 and lo < tick0 <= hi)
