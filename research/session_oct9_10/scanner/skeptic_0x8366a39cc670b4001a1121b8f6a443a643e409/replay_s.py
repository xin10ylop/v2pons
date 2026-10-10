"""Independent amount-specified replay (not the analyst's shift model): every swap is re-executed by its own specified input (a buy: its ETH
in, a0; a sell: its tokens in, a1), at the pool's single range; our buy (end of block B) and sell (head of block S) inserted.
A pull at or before S = stake lost (plus gas)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
Q96 = 1 << 96
STAKE = int(0.0058e18); USD = 15 / 0.0058; GAS_ETH = 0.012 / USD
def sqrt_at_tick(t):
    import math
    return int(math.sqrt(1.0001 ** t) * Q96)
def buy(s, L, eth_in, fee):
    x = eth_in - (eth_in * fee + 999_999) // 1_000_000
    num = L * s; den = L + (x * s) // Q96
    s2 = (num + den - 1) // den
    return s2, (L * (s - s2)) // Q96
def sell(s, L, tok_in, fee):
    x = tok_in - (tok_in * fee + 999_999) // 1_000_000
    s2 = s + (x * Q96) // L
    return s2, (L * (s2 - s) * Q96) // (s * s2)
class Pool:
    def __init__(self, p, e):
        ad = e["adds"][0]; self.add = ad["bn"]; self.L = ad["dl"]; self.lo = ad["lo"]; self.hi = ad["hi"]
        sp0 = p["sqrt_p0"]
        self.s0 = min(sp0, sqrt_at_tick(ad["hi"])) if ad["hi"] < p["tick0"] else sp0
        self.fee = p["fee"]; self.sw = [s for s in e["swaps"] if s["bn"] >= self.add]
        self.pull = e["pulls"][0]["bn"] if e["pulls"] else None
    def check(self):
        s = self.s0; errs = []
        for x in self.sw:
            if x["a0"] < 0: s, _ = buy(s, self.L, -x["a0"], x["fee"])
            else: s, _ = sell(s, self.L, -x["a1"], x["fee"])
            errs.append(abs(s - x["sqrt_p"]) / x["sqrt_p"]); s = x["sqrt_p"]
        return max(errs) if errs else 0
    def trade(self, B, S, stake=STAKE, skip=None):
        """B, S absolute blocks. skip(x) -> True to drop a swap from the replay"""
        if self.pull is not None and self.pull <= B: return {"exit": "pulled_before_buy", "ret": -GAS_ETH / 2 / (stake / 1e18)}
        s = self.s0; i = 0; sw = self.sw
        while i < len(sw) and sw[i]["bn"] <= B:
            x = sw[i]; i += 1
            if skip and skip(x): continue
            s = buy(s, self.L, -x["a0"], x["fee"])[0] if x["a0"] < 0 else sell(s, self.L, -x["a1"], x["fee"])[0]
        s, tok = buy(s, self.L, stake, self.fee)
        if self.pull is not None and self.pull <= S: return {"exit": "pulled", "ret": -1 - GAS_ETH / (stake / 1e18)}
        while i < len(sw) and sw[i]["bn"] < S:
            x = sw[i]; i += 1
            if skip and skip(x): continue
            s = buy(s, self.L, -x["a0"], x["fee"])[0] if x["a0"] < 0 else sell(s, self.L, -x["a1"], x["fee"])[0]
        _, out = sell(s, self.L, tok, self.fee)
        return {"exit": "sold", "ret": (out - stake) / stake - GAS_ETH / (stake / 1e18)}
def summ(rs):
    v = [r["ret"] for r in rs if r["ret"] is not None]
    if not v: return {"n": 0}
    m = st.mean(v)
    return {"n": len(v), "mean": round(m, 4), "median": round(st.median(v), 4), "win": round(sum(a > 0 for a in v) / len(v), 3),
            "pulled": sum(r["exit"] == "pulled" for r in rs), "usd_trade": round(m * 15, 3), "usd_day": round(m * 15 * len(v) / 2.0, 1)}
