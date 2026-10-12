"""Stage 6: the operator's reaction on my slice, a schedule check, and what a $5 front earns.
Reaction: per pool, outside buys >= 0.00003 ETH (not a bot wallet, not the sentinel, not ours) before T (or with no T) and after T; the first
pull after each (to L+200) and its lag.
Schedule: T - L in blocks; best fixed offset within +-1; T - L in seconds (block timestamps).
Front ($5 = 0.001946 ETH; R's integer v4 replay, analysis/R/common.py; fee 1% each way; gas $0.02):
 R0 the candidate rule (a presigned / failed copy of the bot's buy before T): fires in the pools where stage 4 found one -> 0 -> no trade.
 R1 acting on the earliest on-chain form of the bot's intent, its own buy in block T (seen in the feed at T): our buy lands T+1 (latency 1) or
    T+2 (latency 2), behind the bot; sold at the head of the next block, or right behind the bot's 2nd buy; reaction = a pull at our buy + lag.
 R2 (context only; no such signal exists) a precursor at T - lead: our buy lands lead - latency blocks before T (block T = ahead of the bot, the
    best case); sell lands T + latency (sent when the bot's buy is seen); a pull at our buy + lag (a pull in the sell's block counts as lost).
usage: s6_front.py <slice> [lag_min lag_med]"""
import sys, pickle, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
name = sys.argv[1]; kb = KV("blk")
D = pickle.load(open(f"parsed_{name}.pkl", "rb")); ALL = sorted(D["pools"], key=lambda p: p["L"])
print(f"===== slice {name}: pools {len(ALL)}, with a bot buy {sum(1 for p in ALL if p['T'] is not None)}")
pre, post = [], []
for p in ALL:
    pulls = sorted(m["off"] for m in p["ml"] if m["dL"] < 0)
    for o in p["outside"]:
        if o["q"] < 0.00003: continue
        before = p["T"] is None or o["off"] < p["T"] or (o["off"] == p["T"] and o["ti"] < p["Tti"])
        nxt = next((x for x in pulls if x >= o["off"]), None)
        row = (p["L"], o["off"], p["T"], o["eoa"][:10], round(o["q"], 5), nxt, None if nxt is None else nxt - o["off"])
        (pre if before else post).append(row)
def lagstat(rows):
    v = sorted(r[6] for r in rows if r[6] is not None)
    return f"n {len(rows)}, pulled {len(v)}, lags {v}" + (f", min {v[0]} median {st.median(v)}" if v else "")
print("reaction, pre-T outside buys:", lagstat(pre)); [print("   ", r) for r in pre]
first_post = {}
for r in post: first_post.setdefault(r[0], r)
print("reaction, post-T outside buys (first per pool):", lagstat(list(first_post.values()))); [print("   ", r) for r in first_post.values()]
P = [p for p in ALL if p["T"] is not None]
Ts = [p["T"] for p in P]
best = max(range(min(Ts), max(Ts) + 1), key=lambda m: sum(1 for x in Ts if abs(x - m) <= 1))
print(f"\nschedule: T - L blocks p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)}; best fixed offset {best}: within +-1 in {sum(1 for x in Ts if abs(x-best)<=1)} of {len(Ts)}")
secs = collections.Counter()
for p in P:
    bL, bT = kb.d.get(str(p["L"])), kb.d.get(str(p["Tbn"]))
    if bL and bT: secs[bT["ts"] - bL["ts"]] += 1
print(f"   T - L seconds (pools with L's block cached, n {sum(secs.values())}): {sorted(secs.items())}")
q = int(5 / USD * 1e18)
def sw_of(p): return [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
def startL(p):
    adds = [m for m in p["ml"] if m["dL"] > 0]; return adds[0]["dL"] if adds else 0
def run(B, S, p, pull_bn):
    nat = p["L"] + p["pull"] if p["pull"] is not None else None
    pb = min(x for x in (pull_bn, nat) if x is not None) if (pull_bn or nat) else None
    return replay(sw_of(p), SQRT30, startL(p), B, S, q, 10000, 10000, pb)["ret"]
def summ(v):
    v = [x for x in v if x is not None]
    if not v: return "no trades"
    return (f"n {len(v)} mean {100*st.mean(v):+7.2f}% median {100*st.median(v):+7.2f}% p10 {100*pct(v,.1):+7.2f}% p90 {100*pct(v,.9):+7.2f}% "
            f"win {sum(1 for x in v if x > 0)/len(v):.2f} worst {100*min(v):+7.1f}% ${st.mean(v)*5:+.3f}/trade")
lags = [int(x) for x in sys.argv[2:4]] if len(sys.argv) > 3 else [3, 5]
print(f"\nFRONT, $5 = {q/1e18:.6f} ETH; reaction lags modelled: {lags} (min / median of pre-T lags)")
print(" R0 the candidate rule (presigned / failed copy of the bot's buy before T): fires in 0 pools -> 0 trades, $0")
for lat in (1, 2):
    B = lambda p: p["Tbn"] + lat
    for lag in [None] + lags:
        a = [run(B(p), B(p) + 1, p, None if lag is None else B(p) + lag) for p in P]
        b = [run(B(p), p["L"] + p["bot2"] + 1, p, None if lag is None else B(p) + lag) if p["bot2"] else None for p in P]
        tag = "no reaction" if lag is None else f"pull at buy + {lag}"
        print(f" R1 latency {lat} (buy T+{lat}), {tag:18s} | sell next block: {summ(a)}")
        print(f"                                         | sell behind the bot's 2nd buy: {summ(b)}")
print("\n R2 (context: a hypothetical precursor at T - lead; no such signal was found)")
ideal = [run(p["Tbn"], p["Tbn"] + 1, p, None) for p in P]
print(f"   in-time front, no reaction (buy head of T, sell head of T+1): {summ(ideal)}")
for lag in lags:
    for lead in (1, 2, 3, 4):
        for lat in (1, 2):
            v = []
            for p in P:
                Bb = p["Tbn"] - lead + lat; S = p["Tbn"] + lat
                if Bb > p["Tbn"]: v.append(run(Bb, Bb + 1, p, Bb + lag)); continue
                v.append(run(Bb, S, p, Bb + lag) if Bb + lag > S else -1.0 - GAS_USD / 5)
            print(f"   lag {lag} lead {lead} latency {lat}: buy T{lat-lead:+d} sell T+{lat} | {summ(v)}")
