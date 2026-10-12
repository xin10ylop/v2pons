"""Stage 6: replay a $5 front that follows each candidate key on the slice (48 pools, most recent 2 h), with the operator's reaction modelled.
Rule: the engine sees the key's FIRST occurrence in block b >= L+1 (any position ahead of the bot's buy; in T's own block ahead of the bot
counts as d = 0), decides at once, its buy lands at B = b + k (k = 1 or 2 blocks). The operator pulls at B + lag (lag = 3, the minimum of
the 26 measured pre-T lags; 5, their median; and 'emp' = the outcome averaged over all 26 measured lags [3x6, 4x6, 5x4, 6x4, 7x2, 17x2,
18, 23] from ../skeptic2_c4_presign/s5_lags.json). Our sell is sent on seeing the bot's buy at T and lands at T + s (s = 1 or 2).
  B <= T (B = T counted AHEAD of the bot, the best case): pulled (-100% - gas) if B + lag < T + s (a pull in the same block as our sell is
          counted for us, the best case), else the replayed gain of a buy at the head of B sold at the head of T + s;
  B > T: late, a buy behind the bot sold at the head of B + s (replayed; the after-T reaction, 5+ blocks, is slower than that sell);
  no occurrence before the bot's buy: no trade.
Gains: R's integer replay (../../R/common.py, v4 maths from src/), $5 = 5/2570 ETH, fee 1% each way, gas $0.02."""
import pickle, sys, collections, statistics as st, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
os.chdir(HERE)
D = pickle.load(open("s2_parsed.pkl", "rb")); P = {p["pid"]: p for p in D["pools"] if p["in_slice"] and p["T"] is not None}
E = pickle.load(open("s4_rows.pkl", "rb")); rows = E["rows"]
src = open("s5_keys.py").read(); exec(src[src.index("def keys(r):"): src.index("RCP_KEYS")])
LAGS = json.load(open(os.path.join(HERE, "..", "skeptic2_c4_presign", "s5_lags.json")))["pre_T_lags"]
Q = int(5 / USD * 1e18)
def swaps(p): return [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
def gain(p, B, S, pull=None): return replay(swaps(p), SQRT30, p["L0"], B, S, Q, 10000, 10000, pull)["ret"]
# ceiling: a buy at the head of T (ahead of the bot) or T-1, sold at the head of T+1 / T+2, nobody reacts
for B_off, s in ((0, 1), (1, 1), (0, 2), (1, 2)):
    g = [gain(p, p["Tbn"] - B_off, p["Tbn"] + s) for p in P.values()]
    print(f"ceiling (in time, no reaction): buy head of T-{B_off}, sell head of T+{s}: n {len(g)} mean {100*st.mean(g):+.2f}% median {100*st.median(g):+.2f}% min {100*min(g):+.2f}% max {100*max(g):+.2f}%")
first = collections.defaultdict(dict)     # key -> pid -> (d of the first occurrence in L+1.., block)
for r in sorted(rows, key=lambda r: (r["off"], r["ti"])):
    if r["pos"] != "before" or r["off"] < 1: continue
    for k in keys(r) + xkeys(r):
        if r["pid"] not in first[k]: first[k][r["pid"]] = (r["d"], r["L"] + r["off"])
RULES = ["ANY event in another line pool", "touch otherline_3.0:Swap", "to+sel 0x00000000:fd9f1e10", "eth-send other->other", "cls other->other:a9059cbb",
         "cls other->other:095ea7b3", "X bot buy tx (bot router c1120e3d), another pool", "to+sel 0xb740ddd4:00000000", "ANY tx to the PositionManager"]
def outcome(p, b, k, s, lag):
    B = b + k; T = p["Tbn"]
    if B <= T:
        if B + lag < T + s: return "pulled", -1.0 - GAS_USD / 5
        return "in time", gain(p, B, T + s)
    return "late", gain(p, B, B + s)
out = {}
print(f"\nslice pools {len(P)}; per rule: first occurrence d before T (lead), then outcomes for k (buy lands b+k), s (sell lands T+s), lag (pull at our buy + lag)")
for rk in RULES:
    fo = first.get(rk, {}); leads = [fo[pid][0] for pid in P if pid in fo]
    print(f"\n== {rk}: fires in {len(fo)}/{len(P)} pools before the bot's buy; lead d of the first occurrence p10/50/90 {[pct(leads, x) for x in (.1, .5, .9)]}; "
          f"d in 1..2: {sum(1 for d in leads if 1 <= d <= 2)}, d in 1..4: {sum(1 for d in leads if 1 <= d <= 4)}, d 0: {sum(1 for d in leads if d == 0)}, d > 4: {sum(1 for d in leads if d > 4)}")
    print(f"   lead histogram: {sorted(collections.Counter(leads).items())}")
    for k in (1, 2):
        for s in (1, 2):
            for lag in (3, 5, "emp"):
                res = []; cls = collections.Counter()
                for pid, p in P.items():
                    if pid not in fo: continue
                    d, b = fo[pid]
                    if lag == "emp":
                        o = [outcome(p, b, k, s, l) for l in LAGS]; r = st.mean(x[1] for x in o)
                        for x in o: cls[x[0]] += 1 / len(LAGS)
                    else:
                        c, r = outcome(p, b, k, s, lag); cls[c] += 1
                    res.append(r)
                if not res: continue
                m = st.mean(res)
                out[(rk, k, s, lag)] = dict(n=len(res), mean=m, rets=res, cls=dict(cls))
                print(f"   k {k} s {s} lag {lag!s:>3}: trades {len(res):2d} | " + " ".join(f"{c} {v:4.1f}" for c, v in sorted(cls.items())) +
                      f" | mean {100*m:+7.2f}% median {100*st.median(res):+7.2f}% p10 {100*pct(res,.1):+7.2f}% p90 {100*pct(res,.9):+7.2f}% win {sum(1 for x in res if x > 0)/len(res):.2f}"
                      f" | ${5*m:+.2f}/trade, ${5*m*len(res)/2:+.2f}/h")
pickle.dump(out, open("s6_front.pkl", "wb"))
