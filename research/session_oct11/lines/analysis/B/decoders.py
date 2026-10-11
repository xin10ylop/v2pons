"""decode functions copied from s08_decoder.py (decode_launch = flip_engine logic; decode_init = PoolManager.initialize / POSM.initializePool)"""

import pickle, random
from eth_utils import keccak
from common import *
SEL_MULTICALL = "ac9650d8"; SEL_INIT_POOL = "f7020405"; SEL_MODLIQ = "dd46508f"
MIN_SQRT_P = 4295128739; MAX_SQRT_P = 1461446703485210103287273052203988822378723970342
def _u(b, o): return int.from_bytes(b[o:o + 32], "big")
def _s(b, o):
    x = _u(b, o); return x - (1 << 256) if x >> 255 else x
def _dyn(b, base, at):
    st = base + _u(b, at); ln = _u(b, st)
    if st + 32 + ln > len(b): raise ValueError("bytes out of range")
    return st + 32, ln
def decode_launch(data):      # verbatim logic of flip_engine.decode_launch
    b = bytes(data)
    try:
        if len(b) < 68 or b[:4].hex() != SEL_MULTICALL: return None
        arr = 4 + _u(b, 4); n = _u(b, arr)
        if not 0 < n <= 8: return None
        key = sqrt_p = None; mint = None
        for i in range(n):
            st, ln = _dyn(b, arr + 32, arr + 32 + 32 * i); sel = b[st:st + 4].hex()
            if sel == SEL_INIT_POOL and ln >= 196 and key is None:
                k = st + 4; key = (k, b[k:k + 160]); sqrt_p = _u(b, k + 160)
            elif sel == SEL_MODLIQ and mint is None:
                a = st + 4; ust, _ = _dyn(b, a, a); ast, aln = _dyn(b, ust, ust); actions = b[ast:ast + aln]
                parr = ust + _u(b, ust + 32); pn = _u(b, parr)
                for j in range(min(pn, len(actions))):
                    pst, pln = _dyn(b, parr + 32, parr + 32 + 32 * j)
                    if actions[j] == 0x02 and pln >= 384:
                        mint = (b[pst:pst + 160], _s(b, pst + 160), _s(b, pst + 192), _u(b, pst + 224)); break
        if key is None or mint is None or mint[0] != key[1] or not MIN_SQRT_P <= sqrt_p < MAX_SQRT_P or not mint[1] < mint[2]: return None
        kb = key[1]
        return {"pid": "0x" + keccak(kb).hex(), "sqrt_p": sqrt_p, "mint_liq": mint[3], "n_calls": n}
    except Exception:
        return None
def decode_init(data):        # PoolManager.initialize(PoolKey, uint160) / PositionManager.initializePool(PoolKey, uint160)
    b = bytes(data)
    if len(b) < 196 or b[:4].hex() not in ("6276cbbe", "f7020405"): return None
    kb = b[4:164]; return {"pid": "0x" + keccak(kb).hex(), "sqrt_p": _u(b, 164)}
