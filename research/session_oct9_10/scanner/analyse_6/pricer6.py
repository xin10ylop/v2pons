"""analyse_6 pricer: per-pool model from the census + the exact front/follow replay (explore/chk/replay.py's method).

Replay: the pool's start state = the launch price and the active liquidity of its launch mint; every real swap carries its own
shift (a buy: 1/sqrtP moves by its in-range amount / L, measured as Q96/sp_after - Q96/sp_before on the chain; a sell: sqrtP moves by
d_sp), so removing our relay's real swaps (Oct 10 v2.433 pools) and inserting our counterfactual buy keeps every other swap's own
size. Our buy lands at the END of block B (after every other tx of B), our sell at the HEAD of block S. A pull (negative
ModifyLiquidity) at or before S (after our buy) = the whole stake lost (-100% - gas); at or before B = no fill (one leg of gas lost).
A scheduled buy whose own minOut is decodable (the volume bot's router, word 4) and whose output with us ahead falls under it is
dropped (it would revert). Gas: 2 legs x 104,000 x the launch block's base fee. Fees: the fee the pool's Swap events applied (LP +
protocol), the pool key's fee when the pool never swapped.
"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); SCAN = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SCAN, "census")); sys.path.insert(0, "/home/user/v2pons/src")
from load import *  # noqa
import v4math

Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OUR_WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
VBOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"      # chain-wide dust bot: 2e-6 ETH via the UR at launch +2..+4
STAKE = int(0.0058e18)
USD_PER_ETH = 15 / 0.0058
GAS_LEG = 104_000
MIN_REAL = int(0.0002e18)
WINDOW_BLOCKS = 85_203_897 - 83_520_210
WINDOW_DAYS = (1_791_656_447 - 1_791_483_648) / 86400.0      # 48 h census window


def net_in(x, fee): return x - (x * fee + 999_999) // 1_000_000


def sqrt_at_tick(tick):
    """Uniswap TickMath.getSqrtPriceAtTick (exact)"""
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


def pct(v, qs=(.1, .5, .9)):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    return [v[min(len(v) - 1, int(round(a * (len(v) - 1))))] for a in qs]


class Pool:
    def __init__(self, p, e, T, M):
        self.p = p; self.pid = p["pid"]; self.b0 = p["launch_block"]
        e = e or {"swaps": [], "pulls": [], "adds": []}
        self.e = e
        adds = e["adds"]
        # liquidity goes live with the launch tx's adds (else the first add tx)
        live_tx = p["launch_tx"] if any(a["tx"] == p["launch_tx"] for a in adds) else (adds[0]["tx"] if adds else None)
        self.live_tx = live_tx
        self.live_block = next((a["bn"] for a in adds if a["tx"] == live_tx), None)
        rng = [(a["lo"], a["hi"], a["dl"]) for a in adds if a["tx"] == live_tx]
        sp0 = p["sqrt_p0"]
        act = [(lo, hi, d) for lo, hi, d in rng if sqrt_at_tick(lo) < sp0 <= sqrt_at_tick(hi)]
        if act:
            self.s_eff, self.L0 = sp0, sum(d for _, _, d in act)
        else:
            below = [hi for lo, hi, d in rng if sqrt_at_tick(hi) < sp0]
            if below:
                h = max(below); self.s_eff = sqrt_at_tick(h); self.L0 = sum(d for lo, hi, d in rng if lo < h <= hi)
            else:
                self.s_eff, self.L0 = sp0, 0
        fc = collections.Counter(s["fee"] for s in e["swaps"])
        self.fee = fc.most_common(1)[0][0] if fc else p["fee"]
        seq = []; prev = self.s_eff
        for s in e["swaps"]:
            t = T.get(s["tx"]); x = dict(s)
            x["buy"] = s["a0"] < 0; x["eth"] = abs(s["a0"])
            x["relay"] = s["sender"] == RELAY or (t is not None and (t["to"] == RELAY or t["from"] == OUR_WALLET))
            x["in_launch"] = s["tx"] == p["launch_tx"] or s["tx"] == live_tx
            x["to"] = t["to"] if t else None; x["from"] = t["from"] if t else None; x["sel"] = t["selector"] if t else None
            x["input"] = (t.get("input") or t.get("input512")) if t else None
            x["known_tx"] = t is not None
            if x["buy"]: x["d_inv"] = Q96 / s["sqrt_p"] - Q96 / prev
            else: x["d_sp"] = s["sqrt_p"] - prev
            x["prev_sp"] = prev; x["rel"] = s["bn"] - self.b0
            prev = s["sqrt_p"]; seq.append(x)
        self.seq = seq
        self.pulls = e["pulls"]
        self.pull_bn = self.pulls[0]["bn"] if self.pulls else None
        m = M.get(self.b0)
        self.base_fee = m[1] if m else 20_000_000
        self.gas = 2 * GAS_LEG * self.base_fee

    def buys(self):
        """non-launch, non-relay buys"""
        return [x for x in self.seq if x["buy"] and not x["relay"] and not x["in_launch"]]

    @staticmethod
    def _apply(s, x):
        return Q96 / (Q96 / s + x["d_inv"]) if x["buy"] else s + x["d_sp"]

    def state_through(self, bn_incl):
        s = float(self.s_eff); L = self.L0
        for x in self.seq:
            if x["bn"] > bn_incl: break
            if x["relay"]: continue
            s = self._apply(s, x); L = x["liq"]
        return s, L

    def state_before(self, x0):
        """the counterfactual state just before swap x0 (relay swaps removed)"""
        s = float(self.s_eff); L = self.L0
        for x in self.seq:
            if (x["bn"], x["li"]) >= (x0["bn"], x0["li"]): break
            if x["relay"]: continue
            s = self._apply(s, x); L = x["liq"]
        return s, L

    def trade(self, B, S, stake=STAKE, minout=None):
        """our buy at the end of block B, our sell at the head of block S (S > B)"""
        r = {"B": B - self.b0, "S": S - self.b0, "pull": (self.pull_bn - self.b0) if self.pull_bn is not None else None}
        if self.pull_bn is not None and self.pull_bn <= B:
            r.update(exit="pulled_before_buy", ret=-(GAS_LEG * self.base_fee) / stake); return r
        s, L = self.state_through(B)
        if L <= 0:
            r.update(exit="no_liquidity", ret=None); return r
        tokens = v4math.buy_out_int(int(s), L, stake, self.fee)
        s = Q96 / (Q96 / s + net_in(stake, self.fee) / L)
        if self.pull_bn is not None and self.pull_bn <= S:
            r.update(exit="pulled_first", ret=(-stake - self.gas) / stake); return r
        dropped = []
        for x in self.seq:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            if x["relay"]: continue
            L = x["liq"]
            if x["buy"] and minout is not None:
                mo = minout(x)
                if mo is not None and v4math.buy_out_int(int(s), L, x["eth"], x["fee"]) < mo:
                    dropped.append(x["rel"]); continue
            s = self._apply(s, x)
        eth_out = v4math.sell_out_int(int(s), L, tokens, self.fee)
        r.update(exit="sold", ret=(eth_out - stake - self.gas) / stake, gross=(eth_out - stake) / stake, dropped=dropped)
        return r


def vbot_minout(x):
    if x["to"] == VBOT_ROUTER and x["sel"] == "c1120e3d" and x["input"] and len(x["input"]) >= 10 + 64 * 5:
        return int(x["input"][10 + 64 * 4: 10 + 64 * 5], 16)
    return None


def s_after_int(s, L, eth, fee):
    x = net_in(eth, fee); num = L * s; den = L + (x * s) // Q96
    return (num + den - 1) // den


def room(s, L, X, fee, mo):
    """ETH that can be bought ahead of an X-wei buy (from state s, L) before its output falls under mo"""
    if mo is None: return None
    if v4math.buy_out_int(int(s), L, X, fee) < mo: return 0.0
    lo, hi = 0, int(100e18)
    while hi - lo > int(1e12):
        m = (lo + hi) // 2
        if v4math.buy_out_int(s_after_int(int(s), L, m, fee), L, X, fee) >= mo: lo = m
        else: hi = m
    return lo / 1e18


def front(pl, is_sched, minout=None, B_off=1, deadline=20):
    """buy landing at launch + B_off (end of block); sell one block after the first scheduled buy behind ours, capped at launch + deadline"""
    B = pl.b0 + B_off
    sch = [x for x in pl.buys() if is_sched(x)]
    early = [x for x in sch if x["bn"] <= B]
    after = [x for x in sch if x["bn"] > B]
    S = min(after[0]["bn"] + 1, pl.b0 + deadline) if after else pl.b0 + deadline
    r = pl.trade(B, S, minout=minout)
    r["sched_rel"] = after[0]["rel"] if after else None; r["sched_early"] = len(early)
    return r


def follow(pl, hold=4, min_next=MIN_REAL):
    """buy landing one block after the first buy >= 0.0002 ETH; sell one block after the next buy (>= min_next) behind ours, or at our buy + hold"""
    bs = pl.buys()
    trig = next((x for x in bs if x["eth"] >= MIN_REAL), None)
    if trig is None: return None
    B = trig["bn"] + 1
    nxt = next((x for x in bs if x["bn"] > B and x["eth"] >= min_next), None)
    S = min(nxt["bn"] + 1, B + hold) if nxt else B + hold
    r = pl.trade(B, S)
    r["trig_rel"] = trig["rel"]; r["trig_eth"] = trig["eth"] / 1e18; r["next_rel"] = nxt["rel"] if nxt else None
    return r


def summarize(rs, days=WINDOW_DAYS):
    rs = [r for r in rs if r is not None]
    v = [r["ret"] for r in rs if r.get("ret") is not None]
    ex = collections.Counter(r["exit"] for r in rs)
    if not v: return {"n": 0, "exits": dict(ex)}
    m = st.mean(v); usd = m * 15.0
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(a > 0 for a in v) / len(v), 4),
            "pulled_first": ex.get("pulled_first", 0), "pulled_before_buy": ex.get("pulled_before_buy", 0), "exits": dict(ex),
            "usd_trade": round(usd, 4), "trades_day": round(len(v) / days, 1), "usd_day": round(usd * len(v) / days, 2),
            "p10_50_90": [round(a, 4) for a in pct(v)], "min": round(min(v), 4), "max": round(max(v), 4)}


def load_all(pids):
    P = load_pools(); E = load_events(set(pids)); T = load_txs(); M = load_blocks_meta()
    return P, E, T, M
