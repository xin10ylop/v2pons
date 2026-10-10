#!/usr/bin/env python3
"""analyse_4: launch / scheduled buy / pull structure and exact pricing of the front and follow rules, per family.

Data: the census (scanner/census, 48 h to Oct 10 18:20 UTC). Pricing as research/session_oct9_10/explore/chk/replay.py:
  * the pool's own path is rebuilt from the launch state WITHOUT our relay's real swaps (sender 0x2abb5653): every swap is replayed by
    its own shift (an exact-in buy adds Q96*x/L to Q96/sqrtP, a sell adds t/L to sqrtP), shifts measured on the chain's sequence
    (before-state = the previous swap's after-state);
  * our buy (0.0058 ETH) lands at the END of block B (after every other tx of B); tokens = v4math.buy_out_int at the pool's fee;
  * every later swap with B < bn < S is replayed by its own shift on top of our buy; a buy whose own minOut is decodable (the volume
    bot's router c1120e3d, word 4) and whose output with us ahead falls under it is dropped (it reverts);
  * our sell lands at the HEAD of block S: v4math.sell_out_int; a pull (a transaction whose net liquidity change is negative)
    at or before S = the stake lost; at or before B = our buy fails (gas of one leg lost);
  * gas = 2 x 104,000 x the base fee of the launch block (about 0.02 gwei); $ at 0.0058 ETH = $15 (ETH = $2,586).
"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = os.path.join(os.path.dirname(HERE), "census")
sys.path.insert(0, CENSUS); sys.path.insert(0, "/home/user/v2pons/src")
from load import load_pools, load_events, load_txs, load_families, load_blocks_meta   # noqa
import v4math

Q96 = 1 << 96
STAKE = 5_800_000_000_000_000
USD_PER_ETH = 15.0 / 0.0058
GAS_UNITS = 104_000
MIN_REAL = 200_000_000_000_000
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
WINDOW_DAYS = 1_683_688 * 0.1026 / 86400.0


def sqrt_at_tick(tick):
    """Uniswap v4 TickMath.getSqrtPriceAtTick (exact)"""
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


def word(inp, i):
    if not inp or len(inp) < 10 + 64 * (i + 1): return None
    return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def pct(v, qs=(.1, .5, .9), nd=6):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    out = []
    for a in qs:
        x = v[int(round(a * (len(v) - 1)))]
        out.append(round(x, nd) if isinstance(x, float) else x)
    return out


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.pid = p["pid"]; self.b0 = p["launch_block"]
        e = e or {"swaps": [], "pulls": [], "adds": [], "zero_mods": []}
        adds = e["adds"]; pulls = e["pulls"]; swaps = e["swaps"]
        # liquidity live at launch: the adds of the launch tx; else the first add's tx (pools whose mint comes later)
        ltx = p["launch_tx"]
        la = [a for a in adds if a["tx"] == ltx]
        if not la and adds:
            la = [a for a in adds if a["tx"] == adds[0]["tx"]]
        self.live_block = la[0]["bn"] if la else None
        self.live_tx = la[0]["tx"] if la else None
        sp0 = p["sqrt_p0"]; self.sp0 = sp0
        rng = [(a["lo"], a["hi"], a["dl"]) for a in la]
        self.ranges = rng
        act = [d for lo, hi, d in rng if sqrt_at_tick(lo) < sp0 <= sqrt_at_tick(hi)]
        if act:
            self.s_eff = sp0; self.L0 = sum(act); self.start = "in_range"
        else:
            below = [hi for lo, hi, d in rng if sqrt_at_tick(hi) < sp0]
            if below:                                   # a buy walks down to the range's upper edge for free
                h = max(below); self.s_eff = sqrt_at_tick(h); self.L0 = sum(d for lo, hi, d in rng if lo < h <= hi); self.start = "range_below"
            else:
                self.s_eff = sp0; self.L0 = 0; self.start = "no_buy_liquidity" if rng else "no_liquidity"
        fc = collections.Counter(s["fee"] for s in swaps)
        self.fee = fc.most_common(1)[0][0] if fc else (p["fee"] if p["fee"] < 1_000_000 else 0)
        prev = self.s_eff; seq = []
        for s in swaps:
            t = T.get(s["tx"])
            x = dict(s)
            x["buy"] = s["a0"] < 0
            x["eth"] = abs(s["a0"])
            x["relay"] = (s["sender"] == RELAY) or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            x["in_launch"] = s["tx"] == ltx
            x["to"] = t["to"] if t else None; x["from"] = t["from"] if t else None; x["sel"] = t["selector"] if t else None
            x["cdl"] = t["calldata_len"] if t else None
            x["input"] = (t.get("input") or t.get("input512")) if t else None
            x["known_tx"] = t is not None
            if s["a0"] == 0 and s["a1"] == 0:
                x["kind"] = "zero"
            if x["buy"]:
                x["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else:
                x["d_sp"] = s["sqrt_p"] - prev
            prev = s["sqrt_p"]; seq.append(x)
        self.seq = seq
        # pulls: transactions whose net liquidity change is negative (a remove + re-add of the same position in one tx is not a pull)
        net = collections.defaultdict(int); first = {}
        for a in adds + pulls:
            net[a["tx"]] += a["dl"]
            k = (a["bn"], a["ti"])
            if a["tx"] not in first or k < first[a["tx"]]: first[a["tx"]] = k
        self.raw_pulls = pulls
        lmax = max([d for _, _, d in rng] + [self.L0, 0])
        thr = max(1, lmax // 10)
        real = sorted((first[tx], tx, d) for tx, d in net.items() if d < 0 and -d >= thr)
        self.pull_bn = real[0][0][0] if real else None
        self.pull_ti = real[0][0][1] if real else None
        self.pull_tx = real[0][1] if real else None
        self.n_rebalance = sum(1 for tx, d in net.items() if d >= 0 and any(pp["tx"] == tx for pp in pulls))
        meta = M.get(self.b0)
        self.base_fee = meta[1] if meta else 20_092_000

    def gas(self):
        return 2 * GAS_UNITS * self.base_fee

    @staticmethod
    def _apply(s, x):
        if x["buy"]:
            return Q96 / (Q96 / s + x["d_inv"])
        return s + x["d_sp"]

    def state_before(self, bn, li):
        """counterfactual (no relay) state just before log (bn, li)"""
        s = float(self.s_eff); L = self.L0
        for x in self.seq:
            if (x["bn"], x["li"]) >= (bn, li): break
            if x["relay"]: continue
            s = self._apply(s, x); L = x["liq"]
        return s, L

    def trade(self, B, S, stake=STAKE, minout_check=None):
        gas = self.gas()
        if self.L0 <= 0:
            return {"exit": "no_buy_liquidity", "ret": None}
        if self.live_block is None or self.live_block > B:
            return {"exit": "no_liquidity_at_buy", "ret": None}
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": -(GAS_UNITS * self.base_fee) / stake, "B": B - self.b0, "S": S - self.b0}
        s, L = self.state_before(B + 1, -1)
        if L <= 0:
            return {"exit": "no_buy_liquidity", "ret": None}
        tokens = v4math.buy_out_int(int(s), L, stake, self.fee)
        s = Q96 / (Q96 / s + net_in(stake, self.fee) / L)
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
        eth_out = v4math.sell_out_int(int(s), L, tokens, self.fee)
        return {"exit": "sold", "ret": (eth_out - stake - gas) / stake, "gross": (eth_out - stake) / stake, "B": B - self.b0, "S": S - self.b0,
                "dropped": dropped}

    def buys(self):
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"]]


def vbot_minout(x):
    if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"]:
        return word(x["input"], 4)
    return None


def room(s, L, X, fee, mo, hi=10**19):
    """the most ETH that can sit ahead of a buy of X (state s, L) before its output falls under mo (binary search, wei)"""
    if mo is None or L <= 0: return None
    if v4math.buy_out_int(int(s), L, X, fee) < mo: return 0.0
    lo, h = 0, hi
    def out_after(a):
        s2 = Q96 / (Q96 / s + net_in(a, fee) / L)
        return v4math.buy_out_int(int(s2), L, X, fee)
    if out_after(h) >= mo: return float("inf")
    while h - lo > 10**11:
        m = (lo + h) // 2
        if out_after(m) >= mo: lo = m
        else: h = m
    return lo / 1e18


def summarize(rs):
    tr = [r for r in rs if r and r.get("ret") is not None]
    v = [r["ret"] for r in tr]
    ex = collections.Counter(r["exit"] for r in rs if r)
    if not v:
        return {"n": 0, "exits": dict(ex)}
    m = st.mean(v)
    usd_trade = m * STAKE / 1e18 * USD_PER_ETH
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "pulled_before_buy": ex.get("pulled_before_buy", 0), "exits": dict(ex),
            "usd_trade": round(usd_trade, 4), "trades_day": round(len(v) / WINDOW_DAYS, 1), "usd_day": round(usd_trade * len(v) / WINDOW_DAYS, 2),
            "p10_50_90": pct(v, nd=4), "min": round(min(v), 4), "max": round(max(v), 4)}
