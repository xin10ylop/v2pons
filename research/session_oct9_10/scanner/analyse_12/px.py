"""analyse_12 pricer: the exact front/follow replay of research/session_oct9_10/explore/chk/replay.py, rebuilt on the census.

State model:
  - the chain's price path: sqrt_p0 at the Initialize, then the state AFTER each Swap event (sqrt_p, liq); our relay's own swaps
    (Swap sender = the relay) are taken out of the counterfactual (we insert our own trade instead)
  - liquidity: the ranges of every ModifyLiquidity up to a block (adds and pulls), active at a price s when sqrt(lo) < s <= sqrt(hi)
    (a buy moves the price down, so a range whose upper tick is the price is the one it enters: v4math.active_liquidity's rule)
  - our buy lands at the END of block B (after every other tx of B): the chain state after every swap of blocks <= B
  - every later swap (blocks B < bn < S) is replayed by its own price shift: a buy adds its d(1/sqrtP) = Q96/s_after - Q96/s_before,
    a sell its d(sqrtP); in a single range that shift is x_net / L whatever the state ahead of it, so the replay is exact
  - a volume-bot router buy (to 0x1cbaf24d, selector c1120e3d, minOut = calldata word 4) whose output with our buy ahead falls under
    its minOut is dropped (it reverts), as replay.py does
  - our sell lands at the HEAD of block S (it sees every swap of blocks < S)
  - a pull (negative ModifyLiquidity) at or before B: no trade ('pulled_before_buy'); after B and at or before S: the stake lost
  - fees: the LP fee of the pool at our buy and at our sell (two pool fees; a dynamic-fee pool's fee is the one its swaps paid), plus a
    hook's own cut where a receipt shows one (HOOK_TAX, of the ETH in on a buy and of the ETH out on a sell)
  - gas: 2 x 104,000 x the launch block's base fee (about 0.02 gwei: ~$0.011 at $15 per 0.0058 ETH)
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
WINDOW_BLOCKS = 85_203_897 - 83_520_210
WINDOW_DAYS = WINDOW_BLOCKS * 0.1026 / 86400
# hook cuts measured from receipts (fetch.py / peek4-5.py): 0x75a54357 logs 1% of the ETH in on buys (0.0005 of 0.05) and 1% of the ETH out
# on sells (0.000245 of 0.0245025); 0xe693a697 logs 1.5% of the ETH in on buys (1.5e-8 of 1e-6, 1.5e-7 of 1e-5); its sells are unseen: 1.5% assumed
HOOK_TAX = {"0x75a54357d9c78a2db19004a5fdc76c50f9242aec": 10_000, "0xe693a6978cae40520c1aa040ab0ff2d44454f8cc": 15_000}


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
    out = []
    for a in qs:
        x = v[int(round(a * (len(v) - 1)))]
        out.append(round(x, nd) if isinstance(x, float) else x)
    return out


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.pid = p["pid"]; self.b0 = p["launch_block"]; self.fee_key = p["fee"]
        self.tax = HOOK_TAX.get(p["hooks"], 0)
        e = e or {"swaps": [], "pulls": [], "adds": []}
        self.mods = sorted([dict(a, sl=sqrt_at_tick(a["lo"]), sh=sqrt_at_tick(a["hi"])) for a in e["adds"] + e["pulls"]],
                           key=lambda a: (a["bn"], a["li"]))
        self.pulls = e["pulls"]; self.adds = e["adds"]
        self.pull_bn = self.pulls[0]["bn"] if self.pulls else None
        self.pull = self.pulls[0] if self.pulls else None
        prev = p["sqrt_p0"]; seq = []
        for s in e["swaps"]:
            t = T.get(s["tx"]); r = dict(s)
            r["buy"] = s["a0"] < 0; r["eth"] = abs(s["a0"])
            r["relay"] = s["sender"] == RELAY or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            r["in_launch"] = s["tx"] == p["launch_tx"]
            r["to"] = t["to"] if t else None; r["from"] = t["from"] if t else None; r["sel"] = t["selector"] if t else None
            r["input"] = (t.get("input") or t.get("input512")) if t else None
            r["value"] = t["value_wei"] if t else None
            r["pre_sp"] = prev
            if r["buy"]: r["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else: r["d_sp"] = s["sqrt_p"] - prev
            prev = s["sqrt_p"]; seq.append(r)
        self.seq = seq
        meta = M.get(self.b0); self.base_fee = meta[1] if meta else 20_000_000
        self.gas = 2 * GAS_UNITS * self.base_fee

    def L_at(self, s, upto_bn, upto_li=None):
        """active liquidity at price s from the ranges modified up to the end of block upto_bn (or before log index upto_li in it)"""
        L = 0
        for m in self.mods:
            if m["bn"] > upto_bn or (upto_li is not None and m["bn"] == upto_bn and m["li"] >= upto_li): break
            if m["sl"] < s <= m["sh"]: L += m["dl"]
        return L

    def fee_at(self, bn):
        if self.fee_key != 8388608: return self.fee_key
        f = None
        for x in self.seq:
            if f is not None and x["bn"] > bn: break
            f = x["fee"]
        return f if f is not None else 0

    @staticmethod
    def apply(s, x):
        return Q96 / (Q96 / s + x["d_inv"]) if x["buy"] else s + x["d_sp"]

    def state_end_of(self, B):
        """the chain state (our relay's swaps taken out) after every swap of blocks <= B"""
        s = float(self.p["sqrt_p0"])
        for x in self.seq:
            if x["bn"] > B: break
            if x["relay"]: continue
            s = self.apply(s, x)
        return s, self.L_at(s, B)

    def launch_state(self):
        s = float(self.p["sqrt_p0"])
        for x in self.seq:
            if not x["in_launch"]: continue
            s = self.apply(s, x)
        return s, self.L_at(s, self.b0)

    def vbot_minout(self, x):
        if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"] and len(x["input"]) >= 10 + 64 * 5:
            return word(x["input"], 4)
        return None

    def trade(self, B, S, stake=STAKE):
        """our buy lands at the end of block B, our sell at the head of block S"""
        out = {"B": B - self.b0, "S": S - self.b0}
        if self.pull_bn is not None and self.pull_bn <= B:
            return dict(out, exit="pulled_before_buy", ret=None)
        s, L = self.state_end_of(B)
        if L <= 0: return dict(out, exit="no_liquidity", ret=None)
        fb, fs = self.fee_at(B), self.fee_at(S)
        x_in = stake - stake * self.tax // 1_000_000
        tokens = v4math.buy_out_int(int(s), L, x_in, fb)
        s = Q96 / (Q96 / s + net_in(x_in, fb) / L)
        if self.pull_bn is not None and self.pull_bn <= S:
            return dict(out, exit="pulled_first", ret=(-stake - self.gas) / stake, pull=self.pull_bn - self.b0)
        dropped = []
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            if x["buy"]:
                mo = self.vbot_minout(x)
                if mo is not None:
                    Lx = self.L_at(s, x["bn"], x["li"])
                    if v4math.buy_out_int(int(s), Lx, x["eth"], x["fee"]) < mo:
                        dropped.append(x["bn"] - self.b0); continue
            s = self.apply(s, x)
        L = self.L_at(s, S - 1)
        if L <= 0: return dict(out, exit="no_liquidity_at_sell", ret=(-stake - self.gas) / stake)
        eth_out = v4math.sell_out_int(int(s), L, tokens, fs)
        eth_out -= eth_out * self.tax // 1_000_000
        return dict(out, exit="sold", ret=(eth_out - stake - self.gas) / stake, gross=(eth_out - stake) / stake, dropped=dropped)

    def buys(self):
        """non-launch, non-relay buys"""
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"]]

    def validate(self):
        """each buy's output predicted from the chain's own pre-state over its actual output (single-range check)"""
        out = []
        for x in self.seq:
            if not x["buy"] or x["eth"] == 0: continue
            L = self.L_at(x["pre_sp"], x["bn"], x["li"])
            if L <= 0: continue
            # the Swap amount a0 is the input after the hook's cut, before the LP fee
            pred = v4math.buy_out_int(x["pre_sp"], L, x["eth"], x["fee"])
            if x["a1"] > 0: out.append(pred / x["a1"])
        return out


def room(s, L, X, fee, mo):
    """ETH bought ahead from price s before the X-wei buy's output falls under mo"""
    if mo is None: return None
    if mo == 0: return float("inf")
    if v4math.buy_out_int(int(s), L, X, fee) < mo: return 0.0
    lo, hi = 0, int(1000e18)
    while hi - lo > int(1e11):
        m = (lo + hi) // 2
        if v4math.buy_out_int(s_after_buy_int(int(s), L, m, fee), L, X, fee) >= mo: lo = m
        else: hi = m
    return lo / 1e18


def summarize(rs, days=WINDOW_DAYS):
    rs = [r for r in rs if r]
    tr = [r for r in rs if r.get("ret") is not None]
    v = [r["ret"] for r in tr]
    ex = collections.Counter(r["exit"] for r in rs)
    if not v: return {"n": 0, "exits": dict(ex), "usd_trade": 0.0, "usd_day": 0.0, "pulled_first": 0}
    m = st.mean(v); usd = m * STAKE / 1e18 * USD_PER_ETH
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "pulled_before_buy": ex.get("pulled_before_buy", 0), "exits": dict(ex),
            "usd_trade": round(usd, 4), "trades_day": round(len(v) / days, 2), "usd_day": round(usd * len(v) / days, 2),
            "p10_50_90": q(v, nd=5), "min": round(min(v), 5), "max": round(max(v), 5)}


def fmt_rule(s):
    if not s or not s.get("n"): return f"n 0 (exits {s.get('exits') if s else ''})"
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}"
            f"{' (+%d pulled before our buy)' % s['pulled_before_buy'] if s.get('pulled_before_buy') else ''}, ${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day "
            f"({s['trades_day']}/day)")
