"""analyse_16 pricer and helpers: an exact v4 replay in the manner of research/session_oct9_10/explore/chk/replay.py.

  - pool state after the launch tx: Initialize sqrt_p0, active liquidity liq_launch; then every swap of the pool in (bn, li) order;
  - our buy of X wei lands in block B AFTER every other tx of B: our virtual state = the chain's state after its last swap with bn <= B,
    with the swaps of our own relay (sender 0x2abb5653) taken out (their shift skipped); tokens = v4math.buy_out_int(state, L, X, fee);
  - every later swap with B < bn < S is replayed by its own price shift (a buy adds Q96/sp_after - Q96/sp_before to Q96/s, a sell adds
    sp_after - sp_before to s: exact for exact-in swaps inside one range); a volume-bot router buy (to 0x1cbaf24d, c1120e3d) whose output
    with our buy in front falls under its own minOut (calldata word 4) is dropped (it would revert);
  - our sell lands at the head of block S: eth = sell_out_int(replayed state, L, tokens, fee);
  - a pull (negative ModifyLiquidity) with B < bn <= S = the whole stake lost (plus gas); a pull at or before B = no fill (gas only);
  - gas = 2 x 104,000 x the base fee of the launch block (blocks_meta; else 0.02 gwei); two pool fees via buy_out_int/sell_out_int.
"""
import sys, json, statistics as st, collections, math
CENSUS = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census"
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16"
sys.path.insert(0, CENSUS); sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
Q96 = 1 << 96
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
VROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"        # the chain-wide dust bot (2e-6 ETH at +2..+4 in every new pool)
STAKE = 0.0058; X = 5_800_000_000_000_000; USD_PER_ETH = 15 / 0.0058
MIN_REAL = 200_000_000_000_000                            # 0.0002 ETH
GAS_UNITS = 104_000
WINDOW_BLOCKS = 1_683_688
DAYS = WINDOW_BLOCKS * 0.1026 / 86400                     # the census window, 2.0 days


def net(x, fee): return x - (x * fee + 999_999) // 1_000_000


def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)


def pct(v, qs=(0.1, 0.5, 0.9)):
    if not v: return None
    v = sorted(v); n = len(v)
    return [st.median(v) if q == 0.5 else v[min(n - 1, int(q * n))] for q in qs]


class Ctx:
    def __init__(self, pids):
        self.P = load_pools(); self.E = load_events(set(pids)); self.T = load_txs(); self.BM = load_blocks_meta()

    def basefee(self, bn):
        m = self.BM.get(bn)
        return m[1] if m else 20_000_000

    def tx(self, h): return self.T.get(h)


def pool_fee(p, e):
    if p["fee"] & 0x800000:
        fs = [s["fee"] for s in e["swaps"]] if e else []
        return int(st.median(fs)) if fs else 0
    return p["fee"]


def is_bot_buy(t):
    return t is not None and t.get("to") == VROUTER and t.get("selector") == "c1120e3d"


def bot_minout(t):
    return wd(t.get("input") or t.get("input512"), 4)


def buys(ctx, p):
    """the pool's buys, launch tx and our relay excluded"""
    e = ctx.E.get(p["pid"])
    if not e: return []
    return [s for s in e["swaps"] if s["a0"] < 0 and s["tx"] != p["launch_tx"] and s["sender"] != RELAY]


def first_pull(ctx, p):
    e = ctx.E.get(p["pid"])
    return e["pulls"][0] if e and e["pulls"] else None


def replay(ctx, p, B, S, X=X, minout_check=True):
    e = ctx.E.get(p["pid"]); swaps = e["swaps"] if e else []; pulls = e["pulls"] if e else []
    fee = pool_fee(p, e); lb = p["launch_block"]
    gas = 2 * GAS_UNITS * ctx.basefee(lb)
    pull = pulls[0]["bn"] if pulls else None
    if pull is not None and pull <= B:
        return {"exit": "pulled_before_buy", "ret": -gas / X, "pull": pull - lb, "B": B - lb, "S": S - lb}
    s = float(p["sqrt_p0"]); prev = p["sqrt_p0"]; L = p["liq_launch"]
    i = 0
    while i < len(swaps) and swaps[i]["bn"] <= B:
        x = swaps[i]
        if x["sender"] != RELAY:
            if x["a0"] < 0: s = Q96 / (Q96 / s + (Q96 / x["sqrt_p"] - Q96 / prev))
            else: s = s + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]; L = x["liq"]; i += 1
    if L <= 0: return {"exit": "no_liquidity", "ret": None}
    tokens = v4math.buy_out_int(int(s), L, X, fee)
    s = Q96 / (Q96 / s + net(X, fee) / L)
    dropped = []; between = []
    while i < len(swaps) and swaps[i]["bn"] < S:
        x = swaps[i]; i += 1
        if x["sender"] == RELAY:
            prev = x["sqrt_p"]; continue
        if x["liq"] != L: L = x["liq"]
        if x["a0"] < 0:
            t = ctx.tx(x["tx"])
            if minout_check and is_bot_buy(t):
                mo = bot_minout(t); out_us = v4math.buy_out_int(int(s), L, -x["a0"], fee)
                if out_us < mo:
                    dropped.append((x["bn"] - lb, round(out_us / mo, 5))); prev = x["sqrt_p"]; continue
            s = Q96 / (Q96 / s + (Q96 / x["sqrt_p"] - Q96 / prev))
        else:
            s = s + (x["sqrt_p"] - prev)
        between.append((x["bn"] - lb, round(-x["a0"] / 1e18, 7)))
        prev = x["sqrt_p"]
    if pull is not None and pull <= S:
        return {"exit": "pulled_first", "ret": (-X - gas) / X, "pull": pull - lb, "B": B - lb, "S": S - lb}
    eth = v4math.sell_out_int(int(s), L, tokens, fee)
    return {"exit": "sold", "ret": (eth - X - gas) / X, "ret_gross": (eth - X) / X, "B": B - lb, "S": S - lb, "dropped": dropped,
            "between": between[:8], "pull": (pull - lb) if pull is not None else None}


def summ(rs):
    v = [r["ret"] for r in rs if r.get("ret") is not None]
    if not v: return {"n": 0}
    pulled = sum(1 for r in rs if r.get("exit") == "pulled_first")
    m = st.mean(v); usd = m * STAKE * USD_PER_ETH
    return {"n": len(v), "mean": round(m, 5), "median": round(st.median(v), 5), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pulled_first": pulled, "usd_trade": round(usd, 4), "usd_day": round(usd * len(v) / DAYS, 2),
            "min": round(min(v), 4), "max": round(max(v), 4)}


def fmt(s, extra=""):
    if not s or s.get("n", 0) == 0: return "n 0" + (" " + extra if extra else "")
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d, $%+.3f a trade, $%+.2f a day" %
            (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["usd_day"])) + (" " + extra if extra else "")


def front(ctx, p, sched_fn, hold=20, X=X):
    """buy at launch + 1 after the block's other txs; sell one block after the first scheduled buy behind ours, or at launch + hold"""
    lb = p["launch_block"]; B = lb + 1
    sb = sched_fn(ctx, p, B)
    S = min(sb["bn"] + 1, lb + hold) if sb else lb + hold
    r = replay(ctx, p, B, S, X=X)
    r["sched"] = (sb["bn"] - lb) if sb else None
    return r


def follow(ctx, p, hold=4, X=X, min_next=MIN_REAL):
    """buy one block after the first buy >= 0.0002 ETH (launch tx and our relay excluded); sell one block after the next buy >= 0.0002 ETH
    in a later block, or at our buy + hold"""
    lb = p["launch_block"]; bs = buys(ctx, p)
    trig = next((s for s in bs if -s["a0"] >= MIN_REAL), None)
    if trig is None: return None
    B = trig["bn"] + 1
    nxt = next((s for s in bs if s["bn"] > B and -s["a0"] >= min_next), None)
    S = min(nxt["bn"] + 1, B + hold) if nxt else B + hold
    r = replay(ctx, p, B, S, X=X)
    r["trig"] = trig["bn"] - lb; r["trig_eth"] = -trig["a0"] / 1e18; r["next"] = (nxt["bn"] - lb) if nxt else None
    return r


def capacity(ctx, p, sb, slack_assumed=0.99):
    """ETH that can sit ahead of the scheduled buy sb (in one piece at the launch state) before its output falls under its minOut.
    minOut from the bot router calldata (word 4) when it is a c1120e3d buy; otherwise ASSUMED = slack_assumed x the launch-state quote."""
    e = ctx.E[p["pid"]]; fee = pool_fee(p, e); L = p["liq_launch"]; sp = p["sqrt_p0"]; Y = -sb["a0"]
    if L <= 0: return None
    t = ctx.tx(sb["tx"])
    quote = v4math.buy_out_int(sp, L, Y, fee)
    if is_bot_buy(t):
        mo = bot_minout(t); src = "calldata word 4"
    else:
        mo = int(quote * slack_assumed); src = "assumed %.2f x launch quote" % slack_assumed
    if quote < mo: return {"cap_eth": 0.0, "minout_src": src, "minout_over_quote": mo / quote if quote else None}
    lo, hi = 0, 10 ** 20
    while hi - lo > 10 ** 11:
        mid = (lo + hi) // 2
        s2 = int(Q96 / (Q96 / sp + net(mid, fee) / L))
        if v4math.buy_out_int(s2, L, Y, fee) >= mo: lo = mid
        else: hi = mid
    return {"cap_eth": lo / 1e18, "minout_src": src, "minout_over_quote": round(mo / quote, 5), "Y_eth": Y / 1e18}
