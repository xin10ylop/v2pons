"""Skeptic 1: my own replay of a short exit (offline, k01_pools.json). Independent of ../sim.py: the later swaps are carried over by their
REALIZED move of the pool (a buy: the change of Q96/sqrtP between consecutive on-chain Swap logs; a sell: the change of sqrtP), which is
exact for exact-input swaps on one constant-L range whatever the fee field, and needs no rounding model. Our own buy and sell use the
engine's math (src/v4math buy_out_int / sell_out_int, the pool's fee field). Decimal at 80 digits.
  entry: the on-chain state after the last swap in a block <= E (E = the trigger block + 2, our buy at the end of E); in our 5 real
         pools at the real place of our buy, our real buy and sell taken out;
  hold N: the sell is sent when the feed shows E + N and lands at X = E + N + 2: the price after every swap in blocks < X;
  pulled: the pull's block <= X (strict) or < X (lenient, our sell first in the pull's block): -100%;
  take-profit tp cap C: the engine's copy (launch sqrtP, every buy by anyone incl. ours, sells never, apply_buy) checked on each buy
         behind ours up to E + C; ret = (sell_out_int(copy) - stake - 250k x 0.02 gwei) / stake >= tp sends the sell at that buy's
         block, landing + 2; none: the cap's sell as hold C."""
import json, os, sys, decimal
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "..", "..", "..", "..", "..", "src"))
import v4math
decimal.getcontext().prec = 80
Dc = decimal.Decimal; Q96 = 1 << 96; QD = Dc(Q96)
GAS = 20_000_000 * 250_000
def net(x, fee): return x - (x * fee + 999_999) // 1_000_000

def load():
    return json.load(open(os.path.join(H, "k01_pools.json")))

class Sim:
    """one pool's replay with our position. trig: the T offset used (analyst T or the engine's Teng)."""
    def __init__(self, p, trig, stake):
        self.p = p; self.stake = stake; sw = p["sw"]
        ours = [i for i, s in enumerate(sw) if s["c"] == "ours"]
        self.real = bool(ours and sw[ours[0]]["buy"])
        if self.real:
            i0 = ours[0]; self.E = sw[i0]["bn"]
            prev = sw[i0 - 1]["sp"] if i0 > 0 else p["sqrtP0"]; fee0 = sw[i0]["fee"]
            pre = sw[:i0]; post = sw[i0 + 1:]
        else:
            self.E = p["lb"] + trig + 2
            pre = [s for s in sw if s["bn"] <= self.E]; post = [s for s in sw if s["bn"] > self.E]
            prev = pre[-1]["sp"] if pre else p["sqrtP0"]; fee0 = pre[-1]["fee"] if pre else 100
        self.L = sw[0]["liq"]
        # realized moves of every swap (from the on-chain sequence, ours included as the 'previous' state)
        mv = []; last = p["sqrtP0"]
        for s in sw:
            if s["buy"]: mv.append(("b", QD / Dc(s["sp"]) - QD / Dc(last)))
            else: mv.append(("s", Dc(s["sp"]) - Dc(last)))
            last = s["sp"]
        idx = {id(s): k for k, s in enumerate(sw)}
        self.lchg = any(s["liq"] != self.L for s in sw if p["pull"] is None or s["off"] <= p["pull"])
        self.tokens = v4math.buy_out_int(prev, self.L, stake, fee0)
        # our buy: the PoolManager's own rounding (ceil)
        x = net(stake, fee0); den = self.L + (x * prev) // Q96; sp = Dc((self.L * prev + den - 1) // den)
        self.path = [(self.E, sp, fee0)]
        for s in post:
            if s["c"] == "ours": continue
            k, d = mv[idx[id(s)]]
            if k == "b": sp = QD / (QD / sp + d)
            else: sp = sp + d
            self.path.append((s["bn"], sp, s["fee"]))
        self.post = [s for s in post if s["c"] != "ours"]
        self.pullb = p["pullpos"][0] if p["pullpos"] else None
        # the engine's copy just before our buy: launch + every buy before it (sells never), then ours
        cs = float(p["sqrtP0"])
        for s in pre:
            if s["buy"] and s["c"] != "ours": cs = v4math.sqrt_after_buy(cs, self.L, net(s["eth_wei"], 100))
        self.copy0 = v4math.sqrt_after_buy(cs, self.L, net(stake, 100))
    def state_before(self, X):
        st = self.path[0]
        for q in self.path:
            if q[0] < X: st = q
            else: break
        return st
    def ret_at(self, X, lenient=False):
        if self.pullb is not None and (self.pullb < X or (self.pullb == X and not lenient)): return -1.0
        _, sp, fee = self.state_before(X)
        return v4math.sell_out_int(int(sp), self.L, self.tokens, fee) / self.stake - 1
    def hold(self, N, lenient=False): return self.ret_at(self.E + N + 2, lenient)
    def tp(self, tp, cap, lenient=False):
        cs = self.copy0
        for s in self.post:
            if s["bn"] > self.E + cap: break
            if self.pullb is not None and (s["bn"], s["li"]) > tuple(self.p["pullpos"]): break
            if not s["buy"]: continue
            cs = v4math.sqrt_after_buy(cs, self.L, net(s["eth_wei"], 100))
            r = (v4math.sell_out_int(int(cs), self.L, self.tokens, 100) - self.stake - GAS) / self.stake
            if r >= tp: return self.ret_at(s["bn"] + 2, lenient), s["bn"] - self.E
        return self.ret_at(self.E + cap + 2, lenient), cap
