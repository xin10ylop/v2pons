"""analyse_7 pricer: the exact front/follow replay of research/session_oct9_10/explore/chk/replay.py, on the census.

- start state: the launch price sqrt_p0 and the liquidity of the range a buy enters first (v4math.active_liquidity semantics:
  lo < tick0 <= hi, which includes a token-only range whose upper tick is tick0; a range wholly below the price is entered at its
  upper edge, the price jumping there for free)
- every swap of the chain except our own relay's real swaps is replayed by its OWN price shift (a buy adds its d(1/sqrtP), a sell its
  d(sqrtP)); with constant liquidity that is exact whatever the state in front of it; L follows the swap events
- our buy of `stake` wei lands at the END of block B (after every other tx of that block); our sell lands at the HEAD of block S
  (it sees every swap with block < S)
- a volume-bot router buy (0x1cbaf24d, c1120e3d, minOut = calldata word 4) whose output with our buy in front falls under its minOut
  is dropped (it reverts), as replay.py does
- a pull (negative ModifyLiquidity) at or before B: the buy does not fill (its gas lost); after B and at or before S: the whole stake lost
- gas: 2 x 104,000 x the launch block's base fee (about 0.02 gwei); two pool fees (the LP fee in force, from the Swap events)
"""
import sys, os, json, statistics as st, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *  # noqa
import v4math

Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
STAKE = int(0.0058e18)
USD_PER_ETH = 15 / 0.0058
GAS_UNITS = 104_000
MIN_REAL = int(0.0002e18)
WINDOW_DAYS = 1_683_688 * 0.1026 / 86400


def sqrt_at_tick(tick):
    """Uniswap TickMath.getSqrtPriceAtTick"""
    a = -tick if tick < 0 else tick
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 0x1 else 0x100000000000000000000000000000000
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


def net_in(x, fee):
    return x - (x * fee + 999_999) // 1_000_000


def s_after_buy_int(s, L, eth, fee):
    x = net_in(eth, fee); num = L * s; den = L + (x * s) // Q96
    return (num + den - 1) // den


def word(inp, i):
    return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def q(v, qs=(.1, .5, .9), nd=6):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    pick = lambda a: v[int(round(a * (len(v) - 1)))]
    return [round(pick(a), nd) if isinstance(pick(a), float) else pick(a) for a in qs]


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.pid = p["pid"]; self.b0 = p["launch_block"]; self.fee_key = p["fee"]; self.T = T
        e = e or {"swaps": [], "pulls": [], "adds": []}
        adds = e["adds"]; swaps = e["swaps"]
        self.live_tx = adds[0]["tx"] if adds else None
        rng = [(a["lo"], a["hi"], a["dl"]) for a in adds if a["tx"] == self.live_tx]
        sp0 = p["sqrt_p0"]; tick0 = p["tick0"]
        L_act = v4math.active_liquidity(tick0, rng)
        if L_act > 0:
            self.s_eff, self.L0, self.start = sp0, L_act, "active"
        else:
            below = [hi for lo, hi, d in rng if sqrt_at_tick(hi) < sp0]
            if below:
                h = max(below); self.s_eff = sqrt_at_tick(h); self.L0 = sum(d for lo, hi, d in rng if lo < h <= hi); self.start = "below"
            else:
                self.s_eff, self.L0, self.start = sp0, 0, "none"
        prev = self.s_eff; seq = []
        for s in swaps:
            t = T.get(s["tx"]); r = dict(s)
            r["buy"] = s["a0"] < 0; r["eth"] = abs(s["a0"])
            r["relay"] = s["sender"] == RELAY or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            r["in_launch"] = s["tx"] in (p["launch_tx"], self.live_tx)
            r["to"] = t["to"] if t else None; r["from"] = t["from"] if t else None; r["sel"] = t["selector"] if t else None
            r["nonce"] = t["nonce"] if t else None; r["input"] = (t.get("input") or t.get("input512")) if t else None
            r["known_tx"] = t is not None
            if r["buy"]: r["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else: r["d_sp"] = s["sqrt_p"] - prev
            prev = s["sqrt_p"]; seq.append(r)
        self.seq = seq
        self.pulls = e["pulls"]; self.pull_bn = self.pulls[0]["bn"] if self.pulls else None
        meta = M.get(self.b0); self.base_fee = meta[1] if meta else 20_000_000
        self.gas = 2 * GAS_UNITS * self.base_fee

    def fee_at(self, bn):
        if self.fee_key != 8388608: return self.fee_key
        f = None
        for x in self.seq:
            if x["bn"] > bn: break
            f = x["fee"]
        return f if f is not None else (self.seq[0]["fee"] if self.seq else 0)

    @staticmethod
    def apply(s, x):
        return Q96 / (Q96 / s + x["d_inv"]) if x["buy"] else s + x["d_sp"]

    def state_through(self, B):
        s = float(self.s_eff); L = self.L0
        for x in self.seq:
            if x["bn"] > B: break
            if x["relay"]: continue
            s = self.apply(s, x); L = x["liq"]
        return s, L

    def vbot_minout(self, x):
        if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"] and len(x["input"]) >= 10 + 64 * 5:
            return word(x["input"], 4)
        return None

    def trade(self, B, S, stake=STAKE):
        """our buy lands at the end of block B, our sell at the head of block S"""
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": -(GAS_UNITS * self.base_fee) / stake, "B": B - self.b0, "S": S - self.b0}
        s, L = self.state_through(B)
        if L <= 0: return {"exit": "no_liquidity", "ret": None}
        fb, fs = self.fee_at(B), self.fee_at(S)
        tokens = v4math.buy_out_int(int(s), L, stake, fb)
        s = Q96 / (Q96 / s + net_in(stake, fb) / L)
        if self.pull_bn is not None and self.pull_bn <= S:
            return {"exit": "pulled_first", "ret": (-stake - self.gas) / stake, "B": B - self.b0, "S": S - self.b0, "pull": self.pull_bn - self.b0}
        dropped = []
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            L = x["liq"] if x["liq"] else L
            if x["buy"]:
                mo = self.vbot_minout(x)
                if mo is not None and v4math.buy_out_int(int(s), L, x["eth"], x["fee"]) < mo:
                    dropped.append(x["bn"] - self.b0); continue
            s = self.apply(s, x)
        eth_out = v4math.sell_out_int(int(s), L, tokens, fs)
        return {"exit": "sold", "ret": (eth_out - stake - self.gas) / stake, "gross": (eth_out - stake) / stake, "B": B - self.b0, "S": S - self.b0,
                "dropped": dropped}

    def buys(self):
        """non-launch, non-relay buys"""
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"]]


def room(s, L, X, fee, mo):
    """ETH (from price s) that can be bought ahead before the X-wei buy's output falls under mo"""
    if mo is None: return None
    if mo == 0: return float("inf")
    if v4math.buy_out_int(int(s), L, X, fee) < mo: return 0.0
    lo, hi = 0, int(100e18)
    while hi - lo > int(1e11):
        m = (lo + hi) // 2
        if v4math.buy_out_int(s_after_buy_int(int(s), L, m, fee), L, X, fee) >= mo: lo = m
        else: hi = m
    return lo / 1e18


def summarize(rs, days=WINDOW_DAYS):
    tr = [r for r in rs if r and r.get("ret") is not None]
    v = [r["ret"] for r in tr]
    ex = collections.Counter(r["exit"] for r in rs if r)
    if not v: return {"n": 0, "exits": dict(ex)}
    m = st.mean(v); usd = m * STAKE / 1e18 * USD_PER_ETH
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "pulled_before_buy": ex.get("pulled_before_buy", 0), "exits": dict(ex),
            "usd_trade": round(usd, 4), "trades_day": round(len(v) / days, 2), "usd_day": round(usd * len(v) / days, 2),
            "p10_50_90": q(v, nd=5), "min": round(min(v), 5), "max": round(max(v), 5)}


def fmt_rule(s):
    if not s or not s.get("n"): return f"n 0 ({s.get('exits') if s else ''})"
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}"
            f"{' (+%d pulled before our buy)' % s['pulled_before_buy'] if s['pulled_before_buy'] else ''}, ${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day "
            f"({s['trades_day']}/day)")
