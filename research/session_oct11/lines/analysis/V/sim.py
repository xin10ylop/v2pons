"""Verifier's own v4 replay (integer math of src/v4math.py, imported read-only). One active range per pool (checked: no add after the
launch's own mint in any C-1 pool); liquidity is re-read from every Swap event and a change is flagged."""
from common import *
import v4math
from evload import norm
Q96 = 1 << 96
GAS_ETH = 0.02 / ETH_USD


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def sqrt_buy(s, L, eth_in, fee):
    x = net(eth_in, fee); num = L * s; den = L + (x * s) // Q96
    return (num + den - 1) // den


def sqrt_sell(s, L, tok_in, fee):
    return s + (net(tok_in, fee) * Q96) // L


class Pool:
    """events of one ETH-quoted v4 pool (currency0 = ETH) in block order: swaps (bn, ti, li, buy, q, t, L_after, sqrt_after, tx), pulls"""
    def __init__(self, r, o):
        assert r["quote_side"] == 0 and r["dex"] == "v4"
        self.r = r; self.lb = r["launch_block"]; self.fee = r["fee"]
        sw, adds, pulls = norm(r, o)
        ev = {(e[1], e[3]): e for e in o["ev"] if e[0] == "s"}
        self.sw = []
        for s in sw:
            e = ev[(s["bn"], s["li"])]
            self.sw.append((s["bn"], s["ti"], s["li"], s["buy"], s["q"], s["t"], e[9], e[8], s["tx"]))
        self.adds = adds; self.pulls = pulls
        self.L0 = v4math.active_liquidity(r["tick0"], [(a["lo"], a["hi"], a["L"]) for a in adds if a["bn"] == self.lb])
        if self.L0 == 0:   # tick0 exactly on the upper tick: the mint is the only position; use its liquidity
            self.L0 = sum(a["L"] for a in adds if a["bn"] == self.lb)
        self.s0 = r["sqrt_p0"]
        self.late_adds = [a for a in adds if a["bn"] != self.lb]
        self.first_pull = min((p["bn"] for p in pulls), default=None)

    def state_before(self, blk):
        """(sqrt, L) after the last swap in a block < blk"""
        s, L = self.s0, self.L0
        for x in self.sw:
            if x[0] >= blk: break
            s, L = x[7], x[6]
        return s, L

    def replay(self, a, b, q_wei, ours_first=True):
        """buy q at the head of block a, sell everything at the head of block b. -> dict(ret, pulled, ...)"""
        s, L = self.state_before(a)
        if L == 0: return None
        tokens = v4math.buy_out_int(s, L, q_wei, self.fee)
        s = sqrt_buy(s, L, q_wei, self.fee)
        s_after_ours = s; lchg = 0
        for x in self.sw:
            if x[0] < a: continue
            if x[0] >= b: break
            if x[6] != L: lchg += 1; L = x[6]
            s = sqrt_buy(s, L, x[4], self.fee) if x[3] else sqrt_sell(s, L, x[5], self.fee)
        eth = v4math.sell_out_int(s, L, tokens, self.fee)
        ret = (eth - q_wei) / q_wei - GAS_ETH / (q_wei / 1e18)
        fp = self.first_pull
        return {"ret": ret, "raw": (eth - q_wei) / q_wei, "pulled_le": fp is not None and fp <= b, "pulled_lt": fp is not None and fp < b,
                "pulled_before_buy": fp is not None and fp < a, "tokens": tokens, "lchg": lchg, "s_entry": self.state_before(a)[0], "s_after_ours": s_after_ours, "s_exit": s, "L": L}

    def check(self):
        """re-simulate every swap from the launch state without our trade: max relative sqrt error before the first pull"""
        s, L = self.s0, self.L0; worst = 0.0
        for x in self.sw:
            if self.first_pull is not None and x[0] >= self.first_pull: break
            if x[6] != L: L = x[6]
            s = sqrt_buy(s, L, x[4], self.fee) if x[3] else sqrt_sell(s, L, x[5], self.fee)
            worst = max(worst, abs(s - x[7]) / x[7]); s = x[7]
        return worst
