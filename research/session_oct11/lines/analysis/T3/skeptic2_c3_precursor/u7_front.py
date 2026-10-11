"""Stage 7: what a $5 front earns on the test slice with the operator's reaction modelled from the measured pre-T lags (u6b: the first non-dust
outside buy ahead of T in a pool -> the first pull, lag in blocks; min and median used).
Pricing: R's integer v4 replay (analysis/R/common.py, src/v4math), our buy at the HEAD of block B, our sell at the HEAD of block S (S = T+1 is
'right behind the bot's buy'), the pool fee 1% each way, gas $0.02 (R's figure; the live engine's pulled $5 trade showed -$5.15), $5 at
2,570 USD/ETH; the bot's buys dropped when our buy pushes them under their calldata minOut. A modelled pull at B + lag (or the pool's own pull,
whichever first); pull block <= S counts as pulled (tie = pulled; the tie-optimistic variant counts pull == S as survived).
 A. the candidate rule (a touch of pool/token/buyer before T): fires in 0 pools (u4) -> no trades.
 B. upper bound, an oracle that knows T (what a perfect 1-4 block precursor could give an engine landing 1-2 blocks after deciding):
    B in {T-2, T-1, T(head, ahead of the bot)}, S in {T+1, T+2}.
 C. blind rule (no signal): our buy lands at L+k, k fitted on the older pools of the 7 h set, measured on the test slice. If the bot's buy
    lands before the pull, sell at T+1 (seen at T, landed next block, the best case); if not, -100%. Variant 'abort': if no bot buy by B+1,
    sell landing at B+2 (before a pull at >= B+3). Buys landing after T: only if the decision (at B-2) came before T was visible; sold at B+1."""
import pickle, sys, statistics as st, collections, os
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
import v4math
from lib import *
os.chdir(HERE)
STAKE = 5.0; q = int(STAKE / USD * 1e18)
D = pickle.load(open("u2_parsed.pkl", "rb")); R6 = pickle.load(open("u6b_rows.pkl", "rb"))
first = {}
for r in sorted([r for r in R6["rows"] if r["before"] and not r["dust"]], key=lambda r: r["off"]): first.setdefault(r["pid"], r)
lags = sorted(r["lag"] for r in first.values() if r["lag"] is not None)
LMIN, LMED = lags[0], pct(lags, .5)
print(f"measured pre-T reaction (u6b, ~11.5 h): {len(first)} pools with a non-dust outside buy ahead of T, pulled {len(lags)}; lags {lags}; min {LMIN} median {LMED}; "
      f"the bot bought in {sum(1 for r in first.values() if r['T'] is not None)} of them")
def skip(s, sp, L):
    if s.get("who") == "bot" and s.get("minout"): return v4math.buy_out_int(sp, L, s["q"], 10000) < s["minout"]
    return False
def run(p, B, S, lag, tie_ok=False):
    """B, S absolute blocks; lag None = no modelled pull"""
    sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"], who=s["who"], minout=s.get("minout")) for s in p["sw"]]
    pulls = [b for b in ([p["pull_bn"]] if p["pull_bn"] else []) + ([B + lag] if lag is not None else [])]
    pb = min(pulls) if pulls else None
    if pb is not None and tie_ok and pb == S: pb = S + 1
    if pb is not None and pb < p["Tbn"] and B < p["Tbn"] and S > p["Tbn"]:      # pulled before the bot's buy: no bot buy, our tokens dead
        return -1.0 - GAS_USD / STAKE, "pulled_before_T"
    r = replay(sw, SQRT30, p["L0"], B, S, q, 10000, 10000, pb, skip)
    return r["ret"], r["why"]
def summ(v):
    v = [x for x in v if x is not None]
    if not v: return "n 0"
    return (f"n {len(v):3d} mean {100*st.mean(v):+7.2f}% median {100*st.median(v):+7.2f}% win {sum(1 for x in v if x > 0)/len(v):.2f} worst {100*min(v):+7.1f}% "
            f"-100%: {sum(1 for x in v if x <= -0.99)} | ${STAKE*st.mean(v):+.3f}/trade")
TEST = [p for p in D["pools"] if p["recent2h"] and p["T"] is not None and not p["finder"]]
OLD = [p for p in D["pools"] if p["T"] is not None and p not in TEST and p["L"] + p["T"] + 5 < D["head"]]
print(f"test slice {len(TEST)} pools; older pools (for fitting k) {len(OLD)}; stake ${STAKE} = {q/1e18:.6f} ETH")
print("\nA. the candidate rule: fires in 0 of", len(TEST), "test pools (u4_touch.out) -> 0 trades, $0; nothing to time a front on.")
print("\nB. oracle upper bound (T known in advance), test slice:")
for lab, lag in (("no reaction", None), (f"pull at our buy + {LMIN} (min)", LMIN), (f"pull at our buy + {LMED} (median)", LMED)):
    for dB in (0, 1, 2):
        for dS in (1, 2):
            for tie in ((False, True) if lag is not None else (False,)):
                v = [run(p, p["Tbn"] - dB, p["Tbn"] + dS, lag, tie)[0] for p in TEST]
                print(f"  {lab:28s} buy {'T head' if dB == 0 else 'T-%d' % dB:6s} sell T+{dS}{' tie=survive' if tie else '            '}: {summ(v)}")
def blind(S_, k, lag, abort):
    v = []; c = collections.Counter()
    for p in S_:
        B = p["L"] + k; T = p["Tbn"]
        if B <= T:
            if lag is not None and B + lag < T:                         # the pull lands before the bot's buy
                if abort:
                    r, why = run(p, B, B + 2, lag); c["abort" if why != "pulled" else "pulled"] += 1; v.append(r)
                else: c["pulled before T"] += 1; v.append(-1.0 - GAS_USD / STAKE)
            elif abort and T > B + 1:                                     # no bot buy by B+1 -> sell at B+2
                r, why = run(p, B, B + 2, lag); c["abort"] += 1; v.append(r)
            else:
                r, why = run(p, B, T + 1, lag); c["in time" if why == "sold" else why] += 1; v.append(r)
        elif B - 2 < T:                                                     # decided before T was visible: lands behind the bot
            r, why = run(p, B, B + 1, lag); c["late (behind the bot)"] += 1; v.append(r)
        else: c["no trade"] += 1
    return v, c
print("\nC. blind fixed landing offset L+k (no signal): k fitted on the older pools by $ per POOL (no trade = $0), measured on the test slice")
for lag in (LMIN, LMED):
    for abort in (False, True):
        best = None
        for k in range(10, 66):
            v, c = blind(OLD, k, lag, abort)
            per_pool = sum(v) / len(OLD)
            if best is None or per_pool > best[1]: best = (k, per_pool, len(v))
        v, c = blind(TEST, best[0], lag, abort)
        print(f"  pull +{lag} {'abort at B+2' if abort else 'hold to bot ':12s} best k {best[0]} on older ({100*best[1]:+.2f}% of stake per pool, {best[2]} trades) -> test: {summ(v)} {dict(c)}")
        row = []
        for k in range(15, 66, 5):
            vv, cc = blind(TEST, k, lag, abort)
            row.append(f"k{k}:{100*sum(vv)/len(TEST):+.1f}%/{len(vv)}tr")
        print("      test slice, % of stake per pool / trades, by k:", " ".join(row))
        allk = [(round(100 * sum(blind(TEST, k, lag, abort)[0]) / len(TEST), 2), k) for k in range(10, 66)]
        trading = [x for x in allk if blind(TEST, x[1], lag, abort)[0]]
        print(f"      best k ON the test slice (in-sample): {max(allk)}; best k that trades at all: {max(trading) if trading else None}")
# the timing spread (why a blind rule cannot work)
Ts = [p["T"] for p in TEST]
mode_share = max(sum(1 for t in Ts if abs(t - m) <= 1) for m in range(10, 70)) / len(Ts)
print(f"\nT on the test slice: p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)}, best +-1-block window from L holds {100*mode_share:.0f}% of pools")
