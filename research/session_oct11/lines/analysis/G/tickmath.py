"""Uniswap TickMath.getSqrtPriceAtTick (integer), checked against the float 1.0001^(t/2) * 2^96 in g_tickcheck"""
_C = [0xfffcb933bd6fad37aa2d162d1a594001, 0xfff97272373d413259a46990580e213a, 0xfff2e50f5f656932ef12357cf3c7fdcc, 0xffe5caca7e10e4e61c3624eaa0941cd0,
      0xffcb9843d60f6159c9db58835c926644, 0xff973b41fa98c081472e6896dfb254c0, 0xff2ea16466c96a3843ec78b326b52861, 0xfe5dee046a99a2a811c461f1969c3053,
      0xfcbe86c7900a88aedcffc83b479aa3a4, 0xf987a7253ac413176f2b074cf7815e54, 0xf3392b0822b70005940c7a398e4b70f3, 0xe7159475a2c29b7443b29c7fa6e889d9,
      0xd097f3bdfd2022b8845ad8f792aa5825, 0xa9f746462d870fdf8a65dc1f90e061e5, 0x70d869a156d2a1b890bb3df62baf32f7, 0x31be135f97d08fd981231505542fcfa6,
      0x9aa508b5b7a84e1c677de54f3e99bc9, 0x5d6af8dedb81196699c329225ee604, 0x2216e584f5fa1ea926041bedfe98, 0x48a170391f7dc42444e8fa2]
MAX_TICK = 887272
_cache = {}
def sqrt_at(tick):
    v = _cache.get(tick)
    if v is not None: return v
    t = max(-MAX_TICK, min(MAX_TICK, tick)); a = abs(t)
    ratio = _C[0] if a & 1 else 1 << 128
    for i in range(1, 20):
        if a & (1 << i): ratio = (ratio * _C[i]) >> 128
    if t > 0: ratio = ((1 << 256) - 1) // ratio
    v = (ratio >> 32) + (0 if ratio % (1 << 32) == 0 else 1)
    _cache[tick] = v
    return v
