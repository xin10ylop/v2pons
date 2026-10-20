"""Stage 6: a $5 front that follows candidate 4, with the operator's reaction modelled (pull at our buy + 3 = the minimum pre-T lag, and
+ 5 = the median, both re-measured in s5 from 26 pools with an outside buy before T; in 26 of 26 the bot never bought).
Replay: R's integer v4 replay (analysis/R/common.py, validated on 131 real trades), our buy at the head of block B, our sell at the head of S,
fee 1% each way, gas $0.02; the bot's buy reverts when its output after our buy is below its own minOut (calldata word 4 = 95% of the
quote); a pull at or before S is -100% (and a pull at or before T means the bot never buys: 26 of 26 in s5).
Scenarios:
 A. the rule as stated: fire on a visible presigned / failed copy of the bot's buy in [T-4, T-1] (s4, s4b: none in 49 pools) -> no trade;
 B. an upper bound that no engine can reach: an oracle on the bot's signing moment, k blocks before T (the deadline puts k at about 1-4,
    s4 (a)); our buy lands d = 1 or 2 blocks after deciding (B = T-k+d; B >= T means behind the bot's buy), the sell is sent on seeing the bot's
    buy in T's feed and lands T+d;
 C. what the engine can actually see first, the bot's buy itself in block T: buy lands T+d behind it; (C1) flip: sell lands d later;
    (C2) ride: sell right behind the bot's 2nd buy.
Slice: 49 pools with L > 86158232 (none used by the finder)."""
import sys, json, pickle, statistics as st, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
import v4math
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["T"] is not None], key=lambda p: p["L"])
lags = json.load(open("s5_lags.json"))["pre_T_lags"]; LMIN, LMED = min(lags), pct(lags, .5)
q = int(5 / USD * 1e18)
print(f"pools {len(P)}; stake $5 = {q/1e18:.6f} ETH; pre-T pull lags n {len(lags)} min {LMIN} median {LMED}")
for p in P:
    adds = [m for m in p["ml"] if m["dL"] > 0]; p["L0"] = adds[0]["dL"] if adds else 0
    p["rsw"] = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"], bot=s["bot"], minout=(s["w"][4] if s["bot"] else None), off=s["off"]) for s in p["sw"]]
def skip(s, sp, L):
    return s.get("bot") and s.get("minout") is not None and v4math.buy_out_int(sp, L, s["q"], 10000) < s["minout"]
def run(p, B, S, lag):
    r = replay(p["rsw"], SQRT30, p["L0"], B, S, q, 10000, 10000, None if lag is None else B + lag, skip)
    return r
def summ(rets):
    v = [r for r in rets if r is not None]
    if not v: return "no trades"
    return (f"n {len(v)} mean {100*st.mean(v):+.2f}% median {100*st.median(v):+.2f}% win {sum(1 for x in v if x > 0)}/{len(v)} "
            f"-100%: {sum(1 for x in v if x <= -0.99)} min {100*min(v):+.1f}% max {100*max(v):+.1f}% | ${5*st.mean(v):+.3f} a trade, ${5*sum(v):+.2f} total")
print("\nA. the rule as stated (a visible presigned / failed copy of the bot's buy before T): fires in 0 of 49 pools (s4, s4b) -> no trade, $0.")
print("\nB. oracle on the bot's signing moment (not visible on chain or in the feed; an upper bound):")
print("   no reaction (pull ignored), the gain itself:")
for k in (1, 2, 3, 4):
    for d in (1, 2):
        rets = [run(p, p["Tbn"] - k + d if p["Tbn"] - k + d < p["Tbn"] else p["Tbn"] + 1, p["Tbn"] + d if p["Tbn"] - k + d < p["Tbn"] else p["Tbn"] + 1 + d, None)["ret"] for p in P]
        print(f"     k {k} d {d}: {summ(rets)}")
for lab, lag in (("min", LMIN), ("median", LMED)):
    print(f"   reaction: pull at our buy + {lag} ({lab} pre-T lag):")
    for k in (1, 2, 3, 4):
        for d in (1, 2):
            rets = []; why = collections.Counter()
            for p in P:
                T = p["Tbn"]; B = T - k + d
                if B < T: S = T + d; r = run(p, B, S, lag); why["front, " + r["why"] + ("" if r.get("dropped", 0) == 0 else ", bot buy reverted")] += 1
                else: B = T + 1; S = B + d; r = run(p, B, S, lag); why["behind the bot, " + r["why"]] += 1   # same block as the bot's buy: behind it
                rets.append(r["ret"])
            print(f"     k {k} d {d}: {summ(rets)}  {dict(why)}")
print("\nC. the first thing the engine can see is the bot's buy in block T (buy lands T+d behind it):")
for lab, lag in (("no reaction", None), ("min", LMIN), ("median", LMED)):
    for d in (1, 2):
        c1 = [run(p, p["Tbn"] + d, p["Tbn"] + 2 * d, lag)["ret"] for p in P]
        c2 = []
        for p in P:
            b2 = [s["bn"] for s in p["rsw"] if s["bot"] and s["bn"] > p["Tbn"]]
            c2.append(run(p, p["Tbn"] + d, (b2[0] + 1) if b2 else p["Tbn"] + 60, lag)["ret"])
        print(f"   {lab:11s} d {d}: C1 flip {summ(c1)}")
        print(f"   {'':11s} d {d}: C2 ride to the bot's 2nd buy {summ(c2)}")
