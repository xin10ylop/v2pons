"""What the engine would need to recognise a V3 crowd-line launch from its calldata alone (no receipt): the PositionManager multicall
[createAndInitializePoolIfNecessary(token0, token1, fee, sqrtPriceX96) 13ead562, mint(MintParams) 88316456, refundETH() 12210e8a];
the pool address by CREATE2 (factory, keccak(token0, token1, fee), the standard V3 init code hash, checked on this chain); the
liquidity from the mint amounts at the launch price (LiquidityAmounts, exact integers via TickMath)."""
from eth_utils import keccak
FACTORY = bytes.fromhex("1f7d7550b1b028f7571e69a784071f0205fd2efa")
INIT_HASH = bytes.fromhex("e34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54")
WETH = "0bd7d308f8e1639fab988df18a8011f41eacad73"
Q96 = 1 << 96
SEL_MC, SEL_CI, SEL_MINT, SEL_REFUND = "ac9650d8", "13ead562", "88316456", "12210e8a"


def sqrt_at_tick(tick):
    """TickMath.getSqrtRatioAtTick, exact"""
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
        r = ((1 << 256) - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)


def liq_for(sp, sa, sb, a0, a1):
    """LiquidityAmounts.getLiquidityForAmounts (floor, as the PositionManager)"""
    if sa > sb: sa, sb = sb, sa
    l0 = lambda sa, sb: (a0 * ((sa * sb) // Q96)) // (sb - sa)
    l1 = lambda sa, sb: (a1 * Q96) // (sb - sa)
    if sp <= sa: return l0(sa, sb)
    if sp < sb: return min(l0(sp, sb), l1(sa, sp))
    return l1(sa, sb)


def pool_address(t0, t1, fee):
    salt = keccak(bytes.fromhex(t0.zfill(64) + t1.zfill(64) + "%064x" % fee))
    return keccak(b"\xff" + FACTORY + salt + INIT_HASH)[12:].hex()


def _u(b, o): return int.from_bytes(b[o:o + 32], "big")
def _s(b, o):
    x = _u(b, o); return x - (1 << 256) if x >> 255 else x


def decode_launch_v3(data):
    """-> dict or None. Only the line's shape: multicall of exactly [createAndInitialize, mint, refundETH], WETH on one side."""
    b = bytes(data)
    try:
        if len(b) < 68 or b[:4].hex() != SEL_MC: return None
        arr = 4 + _u(b, 4); n = _u(b, arr)
        if n != 3: return None
        calls = []
        for i in range(n):
            st = arr + 32 + _u(b, arr + 32 + 32 * i); ln = _u(b, st)
            if st + 32 + ln > len(b): return None
            calls.append((b[st + 32: st + 36].hex(), st + 36, ln))
        if [c[0] for c in calls] != [SEL_CI, SEL_MINT, SEL_REFUND] or calls[0][2] != 132 or calls[1][2] != 356: return None
        c = calls[0][1]; t0 = b[c + 12:c + 32].hex(); t1 = b[c + 44:c + 64].hex(); fee = _u(b, c + 64); sp = _u(b, c + 96)
        m = calls[1][1]
        if b[m + 12:m + 32].hex() != t0 or b[m + 44:m + 64].hex() != t1 or _u(b, m + 64) != fee: return None
        lo, hi = _s(b, m + 96), _s(b, m + 128); a0, a1 = _u(b, m + 160), _u(b, m + 192); rcpt = b[m + 300:m + 320].hex()
        if WETH not in (t0, t1) or not lo < hi: return None
        qs = 0 if t0 == WETH else 1
        liq = liq_for(sp, sqrt_at_tick(lo), sqrt_at_tick(hi), a0, a1)
        return {"pool": pool_address(t0, t1, fee), "token0": t0, "token1": t1, "token": t1 if qs == 0 else t0, "qs": qs, "fee": fee, "sqrt_p": sp,
                "lo": lo, "hi": hi, "amount0": a0, "amount1": a1, "recipient": rcpt, "liq": liq}
    except Exception:
        return None
