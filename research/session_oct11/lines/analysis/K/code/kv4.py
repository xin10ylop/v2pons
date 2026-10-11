"""the migration pools (v4, ETH/token, fee 0, tick spacing 200, hook 0xe5e70264 taking 1% + the creator fee of the swap's output, one
full-range position): price path from the census events and a full-range constant-product replay of our own trade."""
import json, bisect
from krpc import *
Q96 = 2**96
class V4:
    def __init__(s, pool_row, events):
        s.lb = pool_row["launch_block"]; s.sp0 = pool_row["sqrt_p0"]
        ml = [e for e in events if e[0] == "m" and e[8] > 0]; s.L = ml[0][8] if ml else None
        s.sw = [(e[1], e[3], e[8]) for e in events if e[0] == "s"]; s.bns = [x[0] for x in s.sw]
        s.full_range_only = len([e for e in events if e[0] == "m"]) == 1
    def sqrt_at(s, bn):
        i = bisect.bisect_right(s.bns, bn)
        return s.sw[i - 1][2] if i else s.sp0
    def reserves(s, bn):
        sp = s.sqrt_at(bn); return s.L * Q96 / sp, s.L * sp / Q96      # ETH (currency0), token (currency1), raw units
    def px(s, bn):
        X, Y = s.reserves(bn); return X / Y
    def buy(s, bn, eth_wei, fee):
        X, Y = s.reserves(bn); return Y * eth_wei / (X + eth_wei) * (1 - fee)
    def sell(s, bn, tok, fee):
        X, Y = s.reserves(bn); return X * tok / (Y + tok) * (1 - fee)
