"""Stage 5: a $5 front that follows candidate 2's trigger, with the operator's reaction modelled, on the pools the finder did not use
(regimes 'cur' 04:30-09:37 UTC and 'late' 21:31-22:47 UTC; see s4_rule.py).
Engine: sees the trigger tx (a bot-wallet tx) in the sequencer feed in block b (first such block at or after L+a, before the bot's buy at T),
decides, its buy lands at B = b + k (k = 1 or 2). If the bot's buy came first the engine does not fire (no trade).
Reaction (REPORT_R + r16: every non-dust outside buy before T was followed by a pull, the bot never bought): the pool is pulled at B + lag,
lag = 3 (the minimum observed pre-T lag), 5 (the median of the 27 pre-T cases: 0x8c009ea5 x22, 0x7ae81404 x4, our probe), 9 (our probe).
Our sell is sent when the bot's buy shows in the feed and lands at T + s (s = 0: in T's block behind the bot, optimistic; s = 1: T+1).
  B < T (or B == T counted ahead of the bot, optimistic): pulled at or before T+s -> -100% (if the pull is at or before T the bot never buys);
      else the front's gain: R's integer replay (analysis/R/common.py), our buy at the head of B, sold at the head of T+1, fee 1% each way, gas $0.02.
  B > T: late, a buy right behind the bot sold the next block (replay; no pull within one block).
Baselines on the same pools: an oracle landing at exactly T-1, and blind fixed landing offsets L+k (no trigger)."""
import pickle, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
CUR0 = 85553521; FINDER_START = 85728764; FINDER_LAST = 86150251
D = pickle.load(open("parsed.pkl", "rb")); P = D["pools"]; B_ = KV("blk").d
R4 = pickle.load(open("s4_rule.pkl", "rb")); W = set(R4["W"]); W110 = set(R4["W_finder"])
def regime(p): return "old" if p["L"] < CUR0 else ("cur" if p["L"] < FINDER_START else ("late" if p["L"] > FINDER_LAST else "FINDER"))
STAKE = 5.0; q = int(STAKE / USD * 1e18); LOSS = -1.0 - GAS_USD / STAKE
G = [p for p in P if regime(p) in ("cur", "late") and p["T"] is not None]
for p in G:
    p["reg"] = regime(p)
    adds = [m for m in p["ml"] if m["dL"] > 0]; p["L0"] = adds[0]["dL"] if adds else 0
    p["swr"] = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    ev = {}
    for off in range(1, p["T"] + 1):
        b = B_[str(p["L"] + off)]; cl = set()
        for t in b["tx"]:
            if off == p["T"] and t[7] >= p["Tti"]: continue
            if t[1] in W110: cl.add("ANY tx from the finder's 110")
            if t[1] in W:
                cl.add("ANY bot-wallet tx")
                cl.add("bot buy (another pool)" if (t[2] == BOT and t[3] == "c1120e3d") else "bot-wallet sell via UR" if (t[2] == UR and t[3] == "24856bc3") else "bot-wallet other tx")
        ev[off] = cl
    p["ev"] = ev
GAIN = {}
def gain(p, Bbn, Sbn):
    k = (p["pid"], Bbn, Sbn)
    if k not in GAIN: GAIN[k] = replay(p["swr"], SQRT30, p["L0"], Bbn, Sbn, q, 10000, 10000, None)["ret"]
    return GAIN[k]
def outcome(p, land_off, lag, s):
    """our buy lands at L+land_off -> (kind, ret)"""
    T = p["T"]; Tbn = p["Tbn"]; Bbn = p["L"] + land_off
    if land_off <= T:
        pull = Bbn + lag
        if pull <= Tbn: return "pulled before T", LOSS
        if pull <= Tbn + s: return "pulled before our sell", LOSS
        return "in time", gain(p, Bbn, Tbn + 1)
    return "late", gain(p, Bbn, Bbn + 1)
def run(S, fire, k, lag, s):
    kinds = collections.Counter(); rets = []
    for p in S:
        b = fire(p)
        if b is None: kinds["no trade"] += 1; continue
        kd, r = outcome(p, b + k, lag, s); kinds[kd] += 1; rets.append(r)
    return kinds, rets
def show(label, kinds, rets, n):
    m = st.mean(rets) if rets else 0
    v = sorted(rets)
    print(f"  {label:44s} trades {len(rets):3d}/{n} | in time {kinds['in time']:3d} pulled<T {kinds['pulled before T']:3d} pulled<sell {kinds['pulled before our sell']:3d} "
          f"late {kinds['late']:3d} none {kinds['no trade']:3d} | mean {100*m:7.2f}% (${m*STAKE:+.2f}/trade) median {100*st.median(v) if v else 0:7.2f}% "
          f"p90 {100*pct(v,.9) if v else 0:6.2f}% win {sum(1 for x in v if x > 0)}/{len(v)}")
    return m
for reg in ("cur", "late", "cur+late"):
    S = [p for p in G if p["reg"] == reg or (reg == "cur+late")]
    n = len(S)
    print(f"\n==================== regime {reg}: {n} pools with a bot buy (all with every block L+1..T)")
    g = [gain(p, p["Tbn"] - 1, p["Tbn"] + 1) for p in S]
    print(f"in-time gain of a ${STAKE:.0f} front (buy head of T-1, sold head of T+1, no pull): mean {100*st.mean(g):.2f}% median {100*st.median(g):.2f}% min {100*min(g):.2f}% max {100*max(g):.2f}%")
    print("-- oracle (lands at exactly T-d, no trigger needed), by reaction lag:")
    for lag in (3, 5, 9):
        for s in (0, 1):
            for d in (1, 2, 3):
                kinds, rets = run(S, lambda p, d=d: p["T"] - d, 0, lag, s)
                show(f"oracle land T-{d}  lag {lag} sell T+{s}", kinds, rets, n)
    print("-- blind fixed landing at L+k (best k of 16..60 on these pools, chosen in-sample):")
    for lag in (3, 5, 9):
        best = None
        for kk in range(16, 61):
            kinds, rets = run(S, lambda p, kk=kk: kk, 0, lag, 1)
            m = st.mean(rets) if rets else -9
            if best is None or m > best[0]: best = (m, kk, kinds, rets)
        show(f"blind L+{best[1]}  lag {lag} sell T+1", best[2], best[3], n)
    print("-- the candidate's trigger: first block b >= L+a with the class and b <= T; buy lands b+k")
    for c in ("ANY bot-wallet tx", "ANY tx from the finder's 110", "bot buy (another pool)", "bot-wallet sell via UR", "bot-wallet other tx"):
        for lag, s in ((3, 1), (3, 0), (5, 1), (5, 0), (9, 1)):
            bestrow = None
            for k in (1, 2):
                for a in (1, 4, 10, 15, 20, 25, 30, 35):
                    fire = lambda p, a=a: next((off for off in range(a, p["T"] + 1) if c in p["ev"][off]), None)
                    kinds, rets = run(S, fire, k, lag, s)
                    m = st.mean(rets) if rets else -9
                    if c == "ANY bot-wallet tx" and lag in (3, 5) and s == 1: show(f"{c[:22]} a={a:2d} k={k} lag {lag} sell T+{s}", kinds, rets, n)
                    if bestrow is None or m > bestrow[0]: bestrow = (m, a, k, kinds, rets)
            show(f"BEST {c[:22]} a={bestrow[1]} k={bestrow[2]} lag {lag} sell T+{s}", bestrow[3], bestrow[4], n)
