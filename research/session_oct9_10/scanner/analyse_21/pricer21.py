"""Pool21 = common21.Pool (analyse_20's pricer, verbatim) + one fix: a swap that leaves the pool's liquidity (the Swap event's liquidity
after = 0: e.g. a deployer selling back its whole dev-buy with no price limit sends the price to MAX_SQRT_PRICE through an empty region)
is clamped to the range edge it crossed, and every later swap's own shift is recomputed from the clamped chain prices. Without it the
replay applies the unphysical jump to our shifted state and prices our later sell at 0 (-100%). Moving through an empty region costs
nothing, so the clamp changes no real amounts; it matters only for holds that span such a swap (here: front hold-3000 rows)."""
from common21 import *  # noqa
import common21


class Pool21(common21.Pool):
    def __init__(self, p, e, T, M):
        super().__init__(p, e, T, M)
        edges = sorted(set([sqrt_at_tick(a["lo"]) for a in self.adds if a["lo"] > -887273] + [sqrt_at_tick(a["hi"]) for a in self.adds if a["hi"] < 887273]
                           + [self.s_eff]))
        self.clamped = 0
        prev = self.s_eff
        for x in self.seq:
            sp = x["sqrt_p"]
            if not x["liq"]:
                if x["buy"]:
                    c = [v for v in edges if v <= prev]; sp2 = max(c) if c else sp
                else:
                    c = [v for v in edges if v >= prev]; sp2 = min(c) if c else sp
                if sp2 != sp: self.clamped += 1
                sp = sp2
            if x["buy"]: x["d_inv"] = Q96 / sp - Q96 / prev
            else: x["d_sp"] = sp - prev
            x["pre_sp"] = prev
            prev = sp
