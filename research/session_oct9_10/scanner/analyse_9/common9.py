"""analyse_9 pricer: exact v4 replay in the manner of research/session_oct9_10/explore/chk/replay.py.

Our buy is inserted into the chain's state at the END of block B (after every other tx of that block); every later swap (our own relay's
real swaps removed) is replayed by its own price shift (a buy adds its d(1/sqrtP) = net_in/L, a sell its d(sqrtP)); our sell is priced at
the HEAD of block S (swaps with bn < S applied). A pull (negative ModifyLiquidity) at or before S loses the stake; at or before B: no fill
(gas of one leg). Buys whose minOut is decodable (the volume bot's router c1120e3d, word 4) are dropped when our buy in front pushes their
output under it (they revert). Gas: 2 x 104,000 x the launch block's base fee. Two pool fees (the applied LP fee of the pool's swaps).
"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); SCAN = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SCAN, "census")); sys.path.insert(0, "/home/user/v2pons/src")
from load import *  # noqa
import v4math

Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
STAKE = int(0.0058e18); USD_PER_ETH = 15 / 0.0058; GAS_UNITS = 104_000; MIN_REAL = int(0.0002e18)
WINDOW_DAYS = 1_683_688 * 0.1026 / 86400


def net_in(x, fee): return x - (x * fee + 999_999) // 1_000_000


def sqrt_at_tick(tick):                                     # exact TickMath.getSqrtPriceAtTick
    a = -tick if tick < 0 else tick
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 0x1 else 0x100000000000000000000000000000000
    for bit, m in ((0x2, 0xfff97272373d413259a46990580e213a), (0x4, 0xfff2e50f5f656932ef12357cf3c7fdcc), (0x8, 0xffe5caca7e10e4e61c3624eaa0941cd0),
                   (0x10, 0xffcb9843d60f6159c9db58835c926644), (0x20, 0xff973b41fa98c081472e6896dfb254c0), (0x40, 0xff2ea16466c96a3843ec78b326b52861),
                   (0x80, 0xfe5dee046a99a2a811c461f1969c3053), (0x100, 0xfcbe86c7900a88aedcffc83b479aa3a4), (0x200, 0xf987a7253ac413176f2b074cf7815e54),
                   (0x400, 0xf3392b0822b70005940c7a398e4b70f3), (0x800, 0xe7159475a2c29b7443b29c7fa6e889d9), (0x1000, 0xd097f3bdfd2022b8845ad8f792aa5825),
                   (0x2000, 0xa9f746462d870fdf8a65dc1f90e061e5), (0x4000, 0x70d869a156d2a1b890bb3df62baf32f7), (0x8000, 0x31be135f97d08fd981231505542fcfa6),
                   (0x10000, 0x9aa508b5b7a84e1c677de54f3e99bc9), (0x20000, 0x5d6af8dedb81196699c329225ee604), (0x40000, 0x2216e584f5fa1ea926041bedfe98),
                   (0x80000, 0x48a170391f7dc42444e8fa2)):
        if a & bit: r = (r * m) >> 128
    if tick > 0: r = ((1 << 256) - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)


def q(v, qs=(.1, .5, .9), nd=6):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    return [round(v[int(round(a * (len(v) - 1)))], nd) if isinstance(v[0], float) else v[int(round(a * (len(v) - 1)))] for a in qs]


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.pid = p["pid"]; self.b0 = p["launch_block"]; self.launch_tx = p["launch_tx"]
        e = e or {"swaps": [], "pulls": [], "adds": []}
        adds = e["adds"]; swaps = e["swaps"]
        live_tx = adds[0]["tx"] if adds else None
        rng = [(a["lo"], a["hi"], a["dl"]) for a in adds if a["tx"] == live_tx]
        sp0 = p["sqrt_p0"]
        act = [(lo, hi, d) for lo, hi, d in rng if sqrt_at_tick(lo) < sp0 <= sqrt_at_tick(hi)]
        if act: self.s0 = sp0; self.L0 = sum(d for *_, d in act)
        else:
            below = [hi for lo, hi, d in rng if sqrt_at_tick(hi) < sp0]
            if below:
                h = max(below); self.s0 = sqrt_at_tick(h); self.L0 = sum(d for lo, hi, d in rng if lo < h <= hi)
            else: self.s0 = sp0; self.L0 = 0
        fc = collections.Counter(s["fee"] for s in swaps)
        self.fee = fc.most_common(1)[0][0] if fc else p["fee"]
        prev = self.s0; seq = []
        for s in swaps:
            t = T.get(s["tx"]); x = dict(s)
            x["buy"] = s["a0"] < 0; x["eth"] = abs(s["a0"])
            x["relay"] = s["sender"] == RELAY or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            x["in_launch"] = s["tx"] == self.launch_tx or s["tx"] == live_tx
            x["to"] = t["to"] if t else None; x["from"] = t["from"] if t else None; x["sel"] = t["selector"] if t else None
            x["input"] = (t.get("input") or t.get("input512")) if t else None
            if x["buy"]: x["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else: x["d_sp"] = s["sqrt_p"] - prev
            prev = s["sqrt_p"]; seq.append(x)
        self.seq = seq
        self.pulls = e["pulls"]; self.pull_bn = self.pulls[0]["bn"] if self.pulls else None
        meta = M.get(self.b0); self.base_fee = meta[1] if meta else 20_000_000
        self.gas = 2 * GAS_UNITS * self.base_fee

    @staticmethod
    def _apply(s, x): return Q96 / (Q96 / s + x["d_inv"]) if x["buy"] else s + x["d_sp"]

    def state_through(self, bn_incl, before=None):
        """price/liquidity after every non-relay swap with bn <= bn_incl (or strictly before the (bn, li) position `before`)"""
        s = float(self.s0); L = self.L0
        for x in self.seq:
            if before is not None:
                if (x["bn"], x["li"]) >= before: break
            elif x["bn"] > bn_incl: break
            if x["relay"]: continue
            s = self._apply(s, x); L = x["liq"]
        return s, L

    def buys(self, min_eth=0):
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"] and x["eth"] >= min_eth]

    def trade(self, B, S, stake=STAKE, minout=None):
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": -(GAS_UNITS * self.base_fee) / stake, "B": B - self.b0, "S": S - self.b0}
        s, L = self.state_through(B)
        if L <= 0: return {"exit": "no_liquidity", "ret": None}
        tokens = v4math.buy_out_int(int(s), L, stake, self.fee)
        s = Q96 / (Q96 / s + net_in(stake, self.fee) / L)
        if self.pull_bn is not None and self.pull_bn <= S:
            return {"exit": "pulled_first", "ret": (-stake - self.gas) / stake, "B": B - self.b0, "S": S - self.b0, "pull": self.pull_bn - self.b0}
        dropped = []
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            if x["liq"] != L: L = x["liq"]
            if x["buy"] and minout is not None:
                mo = minout(x)
                if mo is not None and v4math.buy_out_int(int(s), L, x["eth"], x["fee"]) < mo:
                    dropped.append(x["bn"] - self.b0); continue
            s = self._apply(s, x)
        eth_out = v4math.sell_out_int(int(s), L, tokens, self.fee)
        return {"exit": "sold", "ret": (eth_out - stake - self.gas) / stake, "gross": (eth_out - stake) / stake, "B": B - self.b0, "S": S - self.b0, "dropped": dropped}

    # ---- the two rules
    def front(self, is_sched, stake=STAKE, fire_rel=1, fallback_rel=20, minout=None):
        B = self.b0 + fire_rel
        fb = next((x for x in self.buys() if x["bn"] > B and is_sched(x)), None)
        S = fb["bn"] + 1 if fb else self.b0 + fallback_rel
        if fb and S > self.b0 + 3000: S = self.b0 + fallback_rel; fb = None
        r = self.trade(B, S, stake, minout); r["sched_rel"] = fb["bn"] - self.b0 if fb else None
        return r

    def follow(self, stake=STAKE, hold=4, minout=None, trig_min=MIN_REAL):
        bs = self.buys(trig_min)
        if not bs: return None
        trig = bs[0]; B = trig["bn"] + 1
        nb = next((x for x in bs if x["bn"] > B), None)
        S = min(nb["bn"] + 1, B + hold) if nb else B + hold
        r = self.trade(B, S, stake, minout); r["trig_rel"] = trig["bn"] - self.b0; r["trig_eth"] = trig["eth"] / 1e18
        return r


def vbot_minout(x):
    if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"] and len(x["input"]) >= 10 + 64 * 5:
        return int(x["input"][10 + 64 * 4: 10 + 64 * 5], 16)
    return None


def capacity(pool, fb, minout_val=None, cap_hi=int(5e18)):
    """ETH that can sit ahead of the scheduled buy fb before its output falls under minOut. Two numbers:
    total = ETH ahead starting from the launch state (after the launch block, no other swap), extra = ETH on top of the swaps that
    really sat ahead of it on chain. minOut = the decoded one, else 0.99 x the launch-state quote (assumption)."""
    s_launch, L = pool.state_through(pool.b0)
    q0 = v4math.buy_out_int(int(s_launch), L, fb["eth"], fb["fee"])
    assumed = minout_val is None
    mo = minout_val if minout_val is not None else int(q0 * 0.99)
    def room(s_start):
        if v4math.buy_out_int(int(s_start), L, fb["eth"], fb["fee"]) < mo: return 0
        lo, hi = 0, cap_hi
        while hi - lo > int(1e12):
            mid = (lo + hi) // 2
            s = Q96 / (Q96 / s_start + net_in(mid, pool.fee) / L)
            if v4math.buy_out_int(int(s), L, fb["eth"], fb["fee"]) >= mo: lo = mid
            else: hi = mid
        return lo
    s_pre, _ = pool.state_through(None, before=(fb["bn"], fb["li"]))
    return {"minout_assumed": assumed, "minout_over_launch_quote": mo / q0 if q0 else None, "total_eth": room(s_launch) / 1e18, "extra_eth": room(s_pre) / 1e18}


def summarize(rs, days=WINDOW_DAYS):
    rs = [r for r in rs if r is not None]
    tr = [r for r in rs if r.get("ret") is not None]; v = [r["ret"] for r in tr]
    if not v: return {"n": 0}
    m = st.mean(v); usd = m * STAKE / 1e18 * USD_PER_ETH
    ex = collections.Counter(r["exit"] for r in rs)
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "exits": dict(ex), "usd_trade": round(usd, 4), "trades_day": round(len(v) / days, 1),
            "usd_day": round(usd * len(v) / days, 2), "p10_50_90": [round(x, 4) for x in q(v)], "min": round(min(v), 4), "max": round(max(v), 4)}


def load_family_pools(keys):
    F = load_families(); P = load_pools()
    pids = set();
    for k in keys: pids |= set(F[k]["pids"])
    return F, P, load_events(pids), pids
