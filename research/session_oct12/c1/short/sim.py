"""The short-exit simulator (offline, s02_pools.json). One C-1 pool = one active range (the launch position), fee 100. Every swap is replayed
in the pool's own integer math (src/v4math's rounding: a buy of x ETH net of the fee moves sqrtP to ceil(L sqrtP / (L + x sqrtP / Q96)), a
sell of t tokens net of the fee to sqrtP + t Q96 / L), each swap at the size it had on the chain (exact input: the Swap log's ETH for a buy, its
tokens for a sell), with OUR buy of `stake` inserted at the entry point (it shifts every later price: not a linear approximation of it).
Our tokens: v4math.buy_out_int at the entry state; our ETH back: v4math.sell_out_int of those tokens at the state in force when the sell lands.

Exits (the engine's own timing, flip_engine.py):
  hold N: the sell is sent when the feed shows our buy's block + N (send_after = hold_blocks) and lands LAND (2) blocks later: its price
          is the pool after every swap of the blocks before the landing block (ours goes in at the top of its block);
  take-profit tp, cap C: the engine's price copy (launch state, every BUY applied, sells never: apply_buy) is checked on every buy behind
          ours (take_profit: (sell_out_int(copy) - stake - 250,000 x base fee) / stake >= tp); the first that passes sends the sell
          (lands 2 blocks later at the REAL pool price); none by our buy + C: the deadline's sell as hold C.
  -100% when the pool is pulled (the launch wallet's ModifyLiquidity with negative liquidity) in or before the landing block.
"""
from sc import *
Q96 = 1 << 96; FEE = 100; LAND = 2; BASE_FEE = 20_000_000; GAS_RT = BASE_FEE * 250_000      # the engine's round_trip_gas_wei (base fee 0.02 gwei)
def net(x, fee=FEE): return x - (x * fee + 999_999) // 1_000_000
def sp_buy(sp, L, eth_gross, fee=FEE):
    x = net(eth_gross, fee); den = L + (x * sp) // Q96
    return (L * sp + den - 1) // den
def sp_sell(sp, L, tok_gross, fee=FEE): return sp + (net(tok_gross, fee) * Q96) // L
def apply(sp, s):
    """one recorded swap at its own size and its own fee field (100, or 125 once the pool's 25-pip protocol fee is on)"""
    return sp_buy(sp, s["liq"], s["eth_wei"], s["fee"]) if s["buy"] else sp_sell(sp, s["liq"], s["tok"], s["fee"])
def eth_raw(s): return s["eth_wei"]

def load(): return json.load(open(S("s02_pools.json")))

def entry_state(p, Eb):
    """the pool after the last swap at or before block Eb (and its index in sw): the entry point of a T-aligned trade"""
    i = -1
    for k, s in enumerate(p["sw"]):
        if s["bn"] <= Eb: i = k
        else: break
    if i < 0: return None
    s = p["sw"][i]; return i, s["sqrtP"], s["liq"], s["fee"]

class Trade:
    """one simulated position: entry after sw[i0] (state sp0, L0) at block Eb, stake wei; swaps in `skip` (our own real ones) left out"""
    def __init__(self, p, i0, sp0, L0, Eb, stake, skip=(), fee0=FEE):
        self.p = p; self.Eb = Eb; self.stake = stake; self.L0 = L0; self.fee0 = fee0
        self.tokens = v4math.buy_out_int(sp0, L0, stake, fee0)
        sp = sp_buy(sp0, L0, stake, fee0); self.path = [(Eb, sp, L0, fee0)]     # (block, sqrtP after, L, fee) with our buy in
        self.later = [s for s in p["sw"][i0 + 1:] if s["tx"] not in skip]
        for s in self.later:
            L = s["liq"]
            if L > 0: sp = apply(sp, s)
            self.path.append((s["bn"], sp, L, s["fee"]))
        self.pullb = p["pullpos"][0] if p["pullpos"] else None
    def state_before(self, b):
        """the pool (with our buy) after every swap of the blocks before b"""
        st = self.path[0]
        for x in self.path:
            if x[0] < b: st = x
            else: break
        return st
    def ret_at_landing(self, X):
        if self.pullb is not None and self.pullb <= X: return -1.0, "pulled"
        _, sp, L, fee = self.state_before(X)
        if L <= 0: return -1.0, "no liquidity"
        return v4math.sell_out_int(sp, L, self.tokens, fee) / self.stake - 1, "ok"
    def hold(self, N): return self.ret_at_landing(self.Eb + N + LAND)
    def take_profit(self, tp, cap, copy_sp0):
        """copy_sp0: the engine's price copy just before our buy (launch state + every buy up to the entry). Returns (gross return,
        why, send block offset from our buy)"""
        L = self.L0; cs = float(copy_sp0)                                                   # the engine's copy prices with the family's fee (100)
        cs = v4math.sqrt_after_buy(cs, L, net(self.stake))                                  # our own buy (live: apply_buy at our_buy_landed)
        for s in self.later:
            if s["bn"] > self.Eb + cap: break
            if not s["buy"]: continue                                                       # the copy never moves on a sell
            cs = v4math.sqrt_after_buy(cs, L, net(eth_raw(s)))
            if self.pullb is not None and (s["bn"], s["li"]) > tuple(self.p["pullpos"]): break   # the feed shows no buys on a pulled pool
            r = (v4math.sell_out_int(int(cs), L, self.tokens, FEE) - self.stake - GAS_RT) / self.stake
            if r >= tp:
                g, why = self.ret_at_landing(s["bn"] + LAND); return g, "tp " + why, s["bn"] - self.Eb
        g, why = self.ret_at_landing(self.Eb + cap + LAND); return g, "cap " + why, cap

def copy_before(p, upto_pos):
    """the engine's price copy: the launch state with every buy before position upto_pos applied (sells never)"""
    cs = float(SQRTP_OF(p)); L = LIQ
    for s in p["sw"]:
        if (s["bn"], s["li"]) > upto_pos: break
        if s["buy"]: cs = v4math.sqrt_after_buy(cs, L, net(eth_raw(s)))
    return cs

def SQRTP_OF(p): return p["launch_sqrtP"]
