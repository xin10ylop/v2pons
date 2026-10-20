"""Stage 8: what a front on the 3.0 line earns with the reaction modelled, given no precursor (s6) and no schedule (s7).
Gain when it lands in time: R's integer replay (analysis/R/common.py, v4 maths from src/), our $15 buy (0.0058 ETH) at the head of block T
(ahead of the bot's buy), sold at the head of T+1 (behind it), fee 1% each way, gas $0.02.
A blind rule fires so that our buy lands at L+k. Outcomes per pool (reaction from REPORT_R: after a buy before T the operator pulled 3-9
blocks later and the bot never bought, 26 of 26 pools):
  T-2 <= L+k <= T: in time, +gain (our buy in block T counted ahead of the bot's, the best case);
  L+k < T-2: early, the pool is pulled and the bot does not buy: -100%;
  L+k > T but the engine could not see the bot's buy before deciding (decision 2 blocks before landing, T > L+k-2): late, a buy right behind
             the bot, sold the next block: modelled at -2.5% (fees and the bot's impact, optimistic: no pull);
  T <= L+k-2: the engine sees the bot's buy first and does not fire (no trade).
k chosen on the older two thirds, measured on the most recent third."""
import pickle, sys, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["line"] == "3.0" and p["T"] is not None], key=lambda p: p["L"])
q = int(0.0058e18)
for p in P:
    adds = [m for m in p["ml"] if m["dL"] > 0]
    sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    r = replay(sw, SQRT30, adds[0]["dL"] if adds else 0, p["Tbn"], p["Tbn"] + 1, q, 10000, 10000, None)
    p["gain"] = r["ret"]
g = [p["gain"] for p in P if p["gain"] is not None]
print(f"front in time (buy head of T, sell head of T+1), n {len(g)}: mean {100*st.mean(g):.2f}% median {100*st.median(g):.2f}% min {100*min(g):.2f}% max {100*max(g):.2f}%")
n = len(P); disc, hold = P[: (2 * n) // 3], P[(2 * n) // 3:]
def ev(S, k):
    out = {"in": 0, "early": 0, "late": 0, "skip": 0}; rets = []
    for p in S:
        land = k; T = p["T"]
        if T - 2 <= land <= T: out["in"] += 1; rets.append(p["gain"])
        elif land < T - 2: out["early"] += 1; rets.append(-1.0 - GAS_USD / 15)
        elif T > land - 2: out["late"] += 1; rets.append(-0.025)
        else: out["skip"] += 1
    m = st.mean(rets) if rets else 0
    return out, m, len(rets)
print("\nfixed landing offset k: outcome counts and mean return per trade")
best = None
for k in range(16, 64, 2):
    o, m, nt = ev(disc, k)
    if best is None or m > best[1]: best = (k, m)
    print(f"  k {k:2d} discovery: in time {o['in']:3d} early {o['early']:3d} late {o['late']:3d} no trade {o['skip']:3d} | mean {100*m:7.2f}% over {nt} trades")
k = best[0]; o, m, nt = ev(hold, k)
print(f"\nbest k on discovery {k} (mean {100*best[1]:.2f}%); held out: in time {o['in']} early {o['early']} late {o['late']} no trade {o['skip']} | mean {100*m:.2f}% over {nt} trades, ${m*15:.2f} a trade at $15")
need = 0.025 / (st.mean(g) + 1.0)
print(f"break-even: with in-time gain {100*st.mean(g):.2f}% and early -100%, a rule needs in-time / (in-time + early) >= {100/(1+st.mean(g)):.1f}% (ignoring late)")
