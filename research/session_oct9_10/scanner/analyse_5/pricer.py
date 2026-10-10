"""analyse_5 pricer: exact v4 replay of one trade on a census pool, the way research/session_oct9_10/explore/chk/replay.py does it.

- the pool's start state: its launch price and the liquidity of the range a buy enters first (the launch mint; for a token-only range
  below the price, the range's upper edge: a buy walks there for free)
- every swap of the chain (our own relay's real swaps removed) is replayed by its OWN price shift: a buy adds its d(1/sqrtP), a sell its
  d(sqrtP); with constant liquidity that is exact whatever the state in front of it
- our buy of `stake` wei lands at the END of block B (after every other tx of that block); our sell at the HEAD of block S (sees every swap
  with block < S); a scheduled buy whose own minOut we can read is dropped if our buy in front makes it fall under that minOut (it reverts)
- a pull (negative ModifyLiquidity) at or before B: no fill (the buy's gas lost); after B and at or before S: the whole stake lost
- gas: 2 x 104,000 x the launch block's base fee; two pool fees (the fee in force at each leg, from the Swap events)
Adapted from analyse_0/common.py (same method) with the fee taken per leg.
"""
import sys, os, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *          # noqa
import v4math

Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
VBOT_DECOY_ROUTERS = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}
STAKE = int(0.0058e18)
ETH_USD = 15 / 0.0058
GAS_UNITS = 104_000
MIN_REAL = int(0.0002e18)
WINDOW_DAYS = 1_683_688 * 0.1026 / 86400


def sqrt_at_tick(tick):
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


def s_after_int(s, L, eth, fee):
    x = net_in(eth, fee); num = L * s; den = L + (x * s) // Q96
    return (num + den - 1) // den


def q(v, qs=(.1, .5, .9), nd=6):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    pick = lambda a: v[int(round(a * (len(v) - 1)))]
    return [round(pick(a), nd) if isinstance(v[0], float) else pick(a) for a in qs]


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.e = e; self.pid = p["pid"]; self.T = T; self.b0 = p["launch_block"]; self.fee_pool = p["fee"]
        adds = e["adds"] if e else []; swaps = e["swaps"] if e else []
        self.live_block = adds[0]["bn"] if adds else None
        self.live_tx = adds[0]["tx"] if adds else None
        live_adds = [a for a in adds if a["tx"] == self.live_tx] if adds else []
        sp0 = p["sqrt_p0"]; self.sp0 = sp0
        rng = [(a["lo"], a["hi"], a["dl"]) for a in live_adds]
        act = [(lo, hi, d) for lo, hi, d in rng if sqrt_at_tick(lo) < sp0 <= sqrt_at_tick(hi)]
        if act:
            self.s_eff = sp0; self.L0 = sum(d for _, _, d in act)
        else:
            below = [hi for lo, hi, d in rng if sqrt_at_tick(hi) < sp0]
            if below:
                h = max(below); self.s_eff = sqrt_at_tick(h); self.L0 = sum(d for lo, hi, d in rng if lo < h <= hi)
            else:
                self.s_eff = sp0; self.L0 = 0
        self.ranges = rng
        launch_tx = p["launch_tx"]; prev = self.s_eff; seq = []
        for s in swaps:
            t = T.get(s["tx"]); row = dict(s)
            row["buy"] = s["a0"] < 0
            row["eth"] = -s["a0"] if s["a0"] < 0 else s["a0"]
            row["relay"] = (s["sender"] == RELAY) or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            row["in_launch"] = s["tx"] == launch_tx or s["tx"] == self.live_tx
            row["to"] = t["to"] if t else None; row["from"] = t["from"] if t else None; row["sel"] = t["selector"] if t else None
            row["nonce"] = t["nonce"] if t else None; row["clen"] = t["calldata_len"] if t else None
            row["value"] = t["value_wei"] if t else None
            row["input"] = (t.get("input") or t.get("input512")) if t else None
            if row["buy"]: row["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else: row["d_sp"] = s["sqrt_p"] - prev
            prev = s["sqrt_p"]; seq.append(row)
        self.seq = seq
        self.pulls = e["pulls"] if e else []
        self.pull = self.pulls[0] if self.pulls else None
        self.pull_bn = self.pull["bn"] if self.pull else None
        meta = M.get(self.b0)
        self.base_fee = meta[1] if meta else 20_092_000

    def fee_at(self, bn):
        """the swap fee in force at block bn: the last swap's fee at or before it, else the first swap's, else the PoolKey fee"""
        f = None
        for x in self.seq:
            if x["bn"] > bn: break
            f = x["fee"]
        if f is None:
            f = self.seq[0]["fee"] if self.seq else self.fee_pool
        return f

    def gas(self):
        return 2 * GAS_UNITS * self.base_fee

    @staticmethod
    def _apply(s, x):
        return Q96 / (Q96 / s + x["d_inv"]) if x["buy"] else s + x["d_sp"]

    def state_through(self, bn_incl, upto=None):
        """the counterfactual price after every non-relay swap with block <= bn_incl (or before position `upto` = (bn, li))"""
        s = float(self.s_eff); L = self.L0
        for x in self.seq:
            if upto is not None:
                if (x["bn"], x["li"]) >= upto: break
            elif x["bn"] > bn_incl: break
            if x["relay"]: continue
            s = self._apply(s, x); L = x["liq"]
        return s, L

    def trade(self, B, S, stake=STAKE, minout_check=None):
        gas = self.gas()
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": -(GAS_UNITS * self.base_fee) / stake, "B": B - self.b0, "S": S - self.b0}
        s, L = self.state_through(B)
        if L <= 0: return {"exit": "no_liquidity", "ret": None}
        fb = self.fee_at(B); fs = self.fee_at(S)
        tokens = v4math.buy_out_int(int(s), L, stake, fb)
        s = Q96 / (Q96 / s + net_in(stake, fb) / L)
        if self.pull_bn is not None and self.pull_bn <= S:
            return {"exit": "pulled_first", "ret": (-stake - gas) / stake, "B": B - self.b0, "S": S - self.b0, "pull": self.pull_bn - self.b0}
        dropped = []
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            if x["liq"] != L: L = x["liq"]
            if x["buy"] and minout_check is not None:
                mo = minout_check(x)
                if mo is not None and v4math.buy_out_int(int(s), L, x["eth"], x["fee"]) < mo:
                    dropped.append(x["bn"] - self.b0); continue
            s = self._apply(s, x)
        eth_out = v4math.sell_out_int(int(s), L, tokens, fs)
        return {"exit": "sold", "ret": (eth_out - stake - gas) / stake, "gross": (eth_out - stake) / stake, "B": B - self.b0, "S": S - self.b0, "dropped": dropped}

    def buys(self):
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"]]


def room(s, L, X, fee, mo):
    """ETH that can be bought ahead (from price s) before the X-wei buy's output falls under mo"""
    if mo is None: return None
    if mo == 0: return float("inf")
    if v4math.buy_out_int(s, L, X, fee) < mo: return 0.0
    lo, hi = 0, int(100e18)
    while hi - lo > int(1e12):
        m = (lo + hi) // 2
        if v4math.buy_out_int(s_after_int(s, L, m, fee), L, X, fee) >= mo: lo = m
        else: hi = m
    return lo / 1e18


def summarize(rs, per_day_den=WINDOW_DAYS):
    rs = [r for r in rs if r is not None]
    tr = [r for r in rs if r.get("ret") is not None]
    v = [r["ret"] for r in tr]
    if not v: return {"n": 0}
    m = st.mean(v); usd = m * STAKE / 1e18 * ETH_USD
    ex = collections.Counter(r["exit"] for r in rs)
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "pulled_before_buy": ex.get("pulled_before_buy", 0), "exits": dict(ex),
            "usd_trade": round(usd, 4), "trades_day": round(len(v) / per_day_den, 2), "usd_day": round(usd * len(v) / per_day_den, 2),
            "p10_50_90": [round(x, 4) for x in q(v)], "min": round(min(v), 4), "max": round(max(v), 4)}
