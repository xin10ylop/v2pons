"""Stage 6: the operator's reaction re-measured on this slice, and a $5 front that follows each candidate key, replayed with the reaction.
Reaction: every non-dust (>= 0.00003 ETH) outside buy before T in a current-regime 3.0 pool -> blocks to the pull, and whether the bot still bought.
Front: in an armed pool (launched, no bot buy yet) the engine fires at the first block >= L+m that holds the key (read from the feed = the block's
transactions); our buy lands at the head of block sig+delta (delta 1 = fast, 2 = slow); a buy landing in T's own block is counted AHEAD of the
bot's (the best case); we sell when we see the bot's buy, landing at the head of T+delta (a buy that lands after T is sold one block later).
The operator pulls at our buy + lag (lag 3 = the minimum pre-T lag, 5 = the median measured here) or at the pool's own pull if earlier; a pull in
the block our sell lands in counts as a loss ('cons') or as a survival ('opt': our sell at the head of the block wins). Gain: R's integer v4 replay
(analysis/R/common.py: others' swaps re-applied by amount, fee 1% each way, gas $0.02). Stake $5 at $2,570/ETH."""
import pickle, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
E = pickle.load(open("events.pkl", "rb")); rows = E["rows"]
D = pickle.load(open("parsed.pkl", "rb"))
P = sorted([p for p in D["pools"] if p["regime"] == "new" and p["T"] is not None], key=lambda p: p["L"])
ALLNEW = [p for p in D["pools"] if p["regime"] == "new"]
q = int(5 / USD * 1e18)
print(f"current-regime 3.0 pools on this slice: {len(ALLNEW)}, with a bot buy {len(P)}; stake {q/1e18:.5f} ETH ($5)")
# ---- reaction on this slice
print("\n(a) the operator's reaction to non-dust outside buys BEFORE T (current regime, this slice):")
lags = []; nob = 0
for p in ALLNEW:
    T = p["T"] if p["T"] is not None else 10 ** 9
    pre = [o for o in p["outs"] if o["q"] >= 0.00003 and o["off"] < T]
    if not pre: continue
    o = pre[0]; lag = (p["pullbn"] - o["bn"]) if p["pullbn"] is not None else None
    lags.append(lag); nob += p["T"] is not None and p["T"] > o["off"] and (lag is None or p["pull"] > p["T"])
    print(f"   L {p['L']} buy at L+{o['off']} {o['q']:.5f} ETH by {o['eoa'][:10]} via {o['to'][:10]}:{o['sel']}  pull lag {lag}  T {p['T']}")
L_ = [x for x in lags if x is not None]
print(f"  pools {len(lags)}; pulled after it {len(L_)}; lag hist {sorted(collections.Counter(L_).items())}; min {min(L_) if L_ else None} median {st.median(L_) if L_ else None}; "
      f"bot still bought before the pull: {nob}")
# ---- in-time gain (perfect timing) for reference
sw_ = {}
for p in P:
    adds = [m for m in p["ml"] if m["dL"] > 0]
    p["L0"] = adds[0]["dL"] if adds else 0
    sw_[p["pid"]] = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
def outcome(p, B, S, lag, mode):
    pull = p["pullbn"]
    if lag is not None: pull = min(x for x in (pull, B + lag) if x is not None)
    if mode == "opt" and pull is not None and pull == S: pull = None if p["pullbn"] is None or p["pullbn"] > S else p["pullbn"]
    r = replay(sw_[p["pid"]], SQRT30, p["L0"], B, S, q, 10000, 10000, pull)
    return r["ret"]
print("\n(b) perfect timing (an oracle), our buy landing at T-j, sold at T+delta, by reaction lag:")
for j in (0, 1, 2, 3):
    for dl in (1, 2):
        for lag in (None, 3, 5, 9):
            for mode in ("cons", "opt"):
                if lag is None and mode == "opt": continue
                v = [outcome(p, p["Tbn"] - j, p["Tbn"] + dl, lag, mode) for p in P]; v = [x for x in v if x is not None]
                print(f"  land T-{j} sell T+{dl} lag {str(lag):4s} {mode:4s}: n {len(v)} mean {100*st.mean(v):+7.2f}% median {100*st.median(v):+7.2f}% "
                      f"win {100*sum(x>0 for x in v)/len(v):5.1f}% at -100% {100*sum(x<=-0.99 for x in v)/len(v):5.1f}%  ${5*st.mean(v):+.3f}/trade")
# ---- keys as triggers
def keys(r):   # verbatim from the precursor angle's s6_precursors.py (as in s5)
    ks = [f"to+sel {r['tc'] if r['tc'] not in ('other','botwallet','linetoken','otherlauncher','puller') else r['to'][:10]}:{r['sel']}",
          f"cls {r['fc']}->{r['tc']}:{r['sel']}", f"from {r['fc'] if r['fc'] not in ('other',) else r['frm'][:10]}"]
    if r["val"] > 0 and r["sel"] == "": ks.append(f"eth-send {r['fc']}->{r['tc']}")
    if r["to"] == BOT: ks.append("ANY tx to the bot router")
    if any(t.startswith("otherline") for t in r["touch"]): ks.append("ANY event in another line pool")
    return ks
KEYS = ["eth-send other->other", "cls other->other:a9059cbb", "to+sel 0x00000000:fd9f1e10", "cls other->other:095ea7b3", "to+sel 0xccc88a9d:0a2b8f36",
        "cls other->BOTROUTER:c1120e3d", "ANY tx to the bot router", "ANY event in another line pool"]
occ = collections.defaultdict(lambda: collections.defaultdict(set))    # key -> pid -> blocks holding it (before the bot's tx)
pids = {p["pid"] for p in P}
for r in rows:
    if r["pid"] in pids and r["pos"] == "before" and r["d"] >= 1:
        for k in keys(r):
            if k in KEYS: occ[k][r["pid"]].add(r["bn"])
print("\n(c) each key as a trigger: fire at its first block >= L+m before T. 'in time' = buy lands in [T-2, T]; lead = T - signal block of the first fire;"
      "\n    false = blocks holding the key in [L+m, T-5] per pool (each one an early fire); returns with the reaction (lag 3 / 5, cons) and without it")
best = []
for k in KEYS:
    for m in (4, 10, 15, 20, 25, 30, 35, 40):
        for dl in (1, 2):
            res = collections.Counter(); leads = []; falses = []; R = {3: [], 5: [], None: []}
            for p in P:
                sig = sorted(b for b in occ[k].get(p["pid"], ()) if b >= p["L"] + m and b < p["Tbn"])
                falses.append(sum(1 for b in sig if b <= p["Tbn"] - 5))
                if not sig: res["no fire before T"] += 1; continue
                s0 = sig[0]; B = s0 + dl; leads.append(p["Tbn"] - s0)
                if B < p["Tbn"] - 2: res["early"] += 1
                elif B <= p["Tbn"]: res["in time"] += 1
                else: res["late"] += 1
                S = p["Tbn"] + dl if B <= p["Tbn"] else B + 1
                for lag in R: R[lag].append(outcome(p, B, S, lag, "cons"))
            n_tr = len(R[3]); clean = lambda v: [x for x in v if x is not None]
            mm = {lag: (st.mean(clean(v)) if clean(v) else None) for lag, v in R.items()}
            best.append((mm[3] if mm[3] is not None else -9, k, m, dl))
            ld = collections.Counter(min(x, 13) for x in leads)
            print(f"  {k[:30]:30s} m {m:2d} d{dl} fires {n_tr:2d}/{len(P)} in time {res['in time']:2d} early {res['early']:2d} late {res['late']:2d} | lead p10/50/90 "
                  f"{pct(leads,.1)}/{pct(leads,.5)}/{pct(leads,.9)} share lead 1-4 {100*sum(1 for x in leads if 1<=x<=4)/max(1,len(leads)):3.0f}% | false p50 {pct(falses,.5)} | "
                  f"mean lag3 {100*mm[3] if mm[3] is not None else float('nan'):+6.1f}% lag5 {100*mm[5] if mm[5] is not None else float('nan'):+6.1f}% "
                  f"no-react {100*mm[None] if mm[None] is not None else float('nan'):+6.1f}%")
best.sort(reverse=True)
print("\nbest (key, m, delta) in hindsight on this slice by the mean with lag 3:", [(round(100 * b[0], 1), b[1], b[2], b[3]) for b in best[:5]])
# distribution for the hindsight-best rule
b = best[0]; k, m, dl = b[1], b[2], b[3]
for lag in (3, 5):
    v = []
    for p in P:
        sig = sorted(x for x in occ[k].get(p["pid"], ()) if x >= p["L"] + m and x < p["Tbn"])
        if not sig: continue
        B = sig[0] + dl; S = p["Tbn"] + dl if B <= p["Tbn"] else B + 1
        x = outcome(p, B, S, lag, "cons")
        if x is not None: v.append(x)
    print(f"  hindsight-best {k} m {m} delta {dl} lag {lag}: n {len(v)} mean {100*st.mean(v):+.1f}% median {100*st.median(v):+.1f}% p10/p90 "
          f"{100*pct(v,.1):+.1f}/{100*pct(v,.9):+.1f}% win {sum(x>0 for x in v)}/{len(v)} at -100% {sum(x<=-0.99 for x in v)}; ${5*st.mean(v):+.2f} a trade")
print("\n(d) per key, its own hindsight-best (m, delta) on this slice by the lag-3 mean, and the return distribution with lag 3 and lag 5 (cons):")
for k in KEYS:
    bk = max((b for b in best if b[1] == k), key=lambda b: b[0]); m, dl = bk[2], bk[3]
    for lag in (3, 5):
        v = []
        for p in P:
            sig = sorted(x for x in occ[k].get(p["pid"], ()) if x >= p["L"] + m and x < p["Tbn"])
            if not sig: continue
            B = sig[0] + dl; S = p["Tbn"] + dl if B <= p["Tbn"] else B + 1
            x = outcome(p, B, S, lag, "cons")
            if x is not None: v.append(x)
        print(f"  {k[:30]:30s} m {m:2d} d{dl} lag {lag}: n {len(v):2d} mean {100*st.mean(v):+6.1f}% median {100*st.median(v):+6.1f}% p90 {100*pct(v,.9):+5.1f}% "
              f"win {sum(x>0 for x in v):2d}/{len(v):2d} at -100% {sum(x<=-0.99 for x in v):2d}; ${5*st.mean(v):+.2f} a trade")
