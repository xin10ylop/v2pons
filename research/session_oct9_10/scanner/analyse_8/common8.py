"""analyse_8 common: census loading and the exact replay pricer (after research/session_oct9_10/explore/chk/replay.py).

Replay model:
  - the pool's state is rebuilt from the launch state (sqrt_p0, liq_launch) by replaying every swap by its own shift
    (a buy adds its own d(Q96/sqrtP), a sell adds its own d(sqrtP); exact for a single active range), our relay's
    own historical swaps (sender 0x2abb5653) are skipped, so the history is the chain as if we had never traded;
  - our buy of X wei lands at block B AFTER every other transaction of B (integer v4 math at the pool's fee);
  - every later swap is replayed by its own shift; a volume-bot router buy (c1120e3d, minOut = calldata word 4) whose
    output with our buy ahead falls under its minOut is dropped (it reverts);
  - the sell lands at block S at the head of S (after every swap of blocks < S), integer v4 math at the pool's fee;
  - a pull (negative ModifyLiquidity) with B < pull block <= S = the whole stake lost (plus gas); a pull <= B = no trade;
  - gas = 2 x 104,000 x base fee (launch block's base fee from blocks_meta, else 0.02 gwei).
"""
import sys, json, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *          # noqa
import v4math

Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
BOT_ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
STAKE_ETH = 0.0058
STAKE = int(STAKE_ETH * 1e18)
USD_PER_ETH = 15 / STAKE_ETH          # $15 = 0.0058 ETH
REAL = int(0.0002e18)
GAS_UNITS = 2 * 104_000
BLOCK_S = 0.1026
WINDOW_DAYS = 1_683_688 * BLOCK_S / 86400


def wd(inp, i):
    return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def bot_minout(t):
    """the volume bot router's buy: (minOut, amountIn?) from calldata; None if not that call"""
    if not t or (t.get("to") or "") != BOT_ROUTER or t.get("selector") != "c1120e3d": return None
    inp = t.get("input") or t.get("input512")
    try: return wd(inp, 4)
    except Exception: return None


def lp_fee(p, e):
    f = p["fee"]
    if f & 0x800000:
        sw = e.get("swaps") or []
        return sw[0]["fee"] if sw else 0
    return f


def is_relay(x): return x["sender"] == RELAY


class Pool:
    def __init__(self, p, e, T, meta=None):
        self.p = p; self.e = e or {"swaps": [], "pulls": [], "adds": []}
        self.L0 = p["launch_block"]; self.fee = lp_fee(p, self.e)
        self.sw = [x for x in self.e["swaps"]]
        self.relay_swaps = [x for x in self.sw if is_relay(x)]
        self.pulls = self.e["pulls"]
        self.pull_bn = self.pulls[0]["bn"] if self.pulls else None
        self.T = T
        bf = None
        if meta and self.L0 in meta: bf = meta[self.L0][1]
        self.basefee = bf if bf else 20_000_000
        self.gas = GAS_UNITS * self.basefee
        self.liq0 = p["liq_launch"] or 0
        self.sp0 = p["sqrt_p0"]

    def tx(self, x): return self.T.get(x["tx"])

    def buys(self, min_wei=0, after_bn=None, skip_launch=True):
        out = []
        for x in self.sw:
            if x["a0"] >= 0 or is_relay(x): continue
            if skip_launch and x["tx"] == self.p["launch_tx"]: continue
            if -x["a0"] < min_wei: continue
            if after_bn is not None and x["bn"] <= after_bn: continue
            out.append(x)
        return out

    def state_through(self, bn_incl):
        """replayed (s, L) after every non-relay swap of blocks <= bn_incl"""
        s = self.sp0; L = self.liq0; prev = self.sp0
        for x in self.sw:
            if x["bn"] > bn_incl: break
            if x["liq"] > 0 and x["liq"] != L: L = x["liq"]
            if is_relay(x): prev = x["sqrt_p"]; continue
            s = self._shift(s, prev, x); prev = x["sqrt_p"]
        return s, L

    @staticmethod
    def _shift(s, prev, x):
        if x["a0"] < 0:
            d_inv = Q96 * Q96 // x["sqrt_p"] - Q96 * Q96 // prev       # in Q96 * (Q96/sqrtP) units
            return Q96 * Q96 // (Q96 * Q96 // s + d_inv)
        return s + (x["sqrt_p"] - prev)

    def trade(self, B, S, X=STAKE, check_bot=True, ahead_extra=0):
        """our buy of X wei lands at the end of block B, the sell at the head of block S (> B)."""
        if self.pull_bn is not None and self.pull_bn <= B:
            return {"exit": "pulled_before_buy", "ret": None, "B": B - self.L0, "S": S - self.L0}
        s = self.sp0; L = self.liq0; prev = self.sp0
        i = 0; n = len(self.sw)
        while i < n and self.sw[i]["bn"] <= B:
            x = self.sw[i]
            if x["liq"] > 0 and x["liq"] != L: L = x["liq"]
            if not is_relay(x): s = self._shift(s, prev, x)
            prev = x["sqrt_p"]; i += 1
        if L <= 0: return {"exit": "no_liquidity", "ret": None}
        s_pre = s
        if ahead_extra:
            xa = ahead_extra - (ahead_extra * self.fee + 999_999) // 1_000_000
            s = Q96 * Q96 // (Q96 * Q96 // s + xa * Q96 // L)
        tokens = v4math.buy_out_int(s, L, X, self.fee)
        xn = X - (X * self.fee + 999_999) // 1_000_000
        num = L * s; den = L + (xn * s) // Q96
        s = (num + den - 1) // den
        dropped = []
        while i < n and self.sw[i]["bn"] < S:
            x = self.sw[i]
            if x["liq"] > 0 and x["liq"] != L: L = x["liq"]
            if is_relay(x): prev = x["sqrt_p"]; i += 1; continue
            if x["a0"] < 0 and check_bot:
                mo = bot_minout(self.tx(x))
                if mo is not None:
                    out_us = v4math.buy_out_int(s, L, -x["a0"], self.fee)
                    if out_us < mo:
                        dropped.append(x["bn"] - self.L0); prev = x["sqrt_p"]; i += 1; continue
            s = self._shift(s, prev, x); prev = x["sqrt_p"]; i += 1
        gas = self.gas
        if self.pull_bn is not None and self.pull_bn <= S:
            return {"exit": "pulled_first", "ret": (-X - gas) / X, "B": B - self.L0, "S": S - self.L0, "pull": self.pull_bn - self.L0, "dropped": dropped}
        eth_out = v4math.sell_out_int(s, L, tokens, self.fee)
        return {"exit": "sold", "ret": (eth_out - X - gas) / X, "ret_gross": (eth_out - X) / X, "B": B - self.L0, "S": S - self.L0, "dropped": dropped}

    def check_replay(self):
        """max relative error between the replayed sqrtP and the recorded one, over swaps not preceded by a relay swap"""
        s = self.sp0; prev = self.sp0; worst = 0.0; seen_relay = False
        for x in self.sw:
            if is_relay(x): seen_relay = True; prev = x["sqrt_p"]; continue
            s = self._shift(s, prev, x); prev = x["sqrt_p"]
            if not seen_relay and x["liq"] > 0:
                worst = max(worst, abs(s - x["sqrt_p"]) / x["sqrt_p"])
        return worst


def stats(rets, pulled=None, per_day=None, n_pools=None):
    v = [r for r in rets if r is not None]
    if not v: return {"n": 0}
    m = st.mean(v)
    out = {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 3),
           "min": round(min(v), 4), "max": round(max(v), 4), "usd_trade": round(m * 15, 4)}
    if pulled is not None: out["pulled_first"] = pulled
    if per_day is not None and n_pools:
        out["usd_day"] = round(m * 15 * per_day * len(v) / n_pools, 2)
    return out


def pct(v, qs=(10, 50, 90)):
    v = sorted(v)
    if not v: return None
    return [v[min(len(v) - 1, int(q / 100 * len(v)))] for q in qs]
