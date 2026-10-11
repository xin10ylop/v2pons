"""Stage 4: candidate 2 re-measured from whole blocks (every transaction, failed ones included) on the most recent 2 hours of 3.0 pools, with
the 4 hours before as a second, older out-of-sample set.
Candidate: 'any transaction from one of the bot's buyer wallets (buys c1120e3d to the router 0x1cbaf24d, or sells 24856bc3 to the Universal
Router), in another pool, seen in the window; buy so that it lands 1-2 blocks later.'
Bot wallets = senders of c1120e3d to 0x1cbaf24d seen anywhere in this angle's data (9 h of 3.0 pool swaps and 6 h of whole blocks around
3.0 pools, both lines' buys inside those blocks). CAUSAL: a wallet counts at block b only if it was first seen before b (default);
--full uses every wallet ever seen (a look-ahead, more fires).
Precursor = a tx in blocks [L+1, T] (in T's block only ahead of the bot's buy) from a bot wallet whose input does not carry this pool's
token or pool id. d = T - (precursor block). Variants: W0 the candidate (any tx); W1 buys (c1120e3d to the router); W2 sells (24856bc3 to the
UR); W3 anything else from a bot wallet; W4 = the T buyer's own previous tx (look-ahead: the engine cannot know the buyer; information only).
Engine: it reads the sequencer feed, so a precursor in block b is seen when b is sequenced; it decides and its buy lands at b+k (k = 1, 2).
Reaction (pre-T outside buys, stage 2, 23 pools: lags 3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,6,6,6,9,17,17,18,23, min 3, median 4): pull at landing + lag.
  landing < T and landing + lag <= T: pulled before the bot buys: -100%;
  landing <= T (T: ahead of the bot's buy in T's block, the best case): our sell (sent on seeing the bot's buy) lands at T+s (s = 1; s = 0 the
    optimistic same-block case); survives iff landing + lag > T+s, or = T+s with the tie counted for us; else -100%;
    gain from the integer replay (R/common.replay: buy at the head of landing, sell at the head of T+s+... see gret);
  landing > T: late, a buy behind the bot's buy sold at the head of the next block (replayed, no pull);
  no precursor in [L+a, T]: no trade.
$5 stake (0.001946 ETH at $2,570), gas $0.02 a trade (R's figures)."""
import pickle, sys, os, json, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from lib import *
from common import replay, GAS_USD, USD
os.chdir(HERE)
FULL = "--full" in sys.argv
FINDER_LAST_L = 86150251                   # the precursor angle's last 3.0 pool (its pools.json); "new" = launched after it
D = pickle.load(open("s2_parsed.pkl", "rb")); ALL = D["pools"]
lo2 = D["head"] - int(2 * 3600 * D["bps"]); lo6 = D["head"] - int(6 * 3600 * D["bps"])
kb = KV("blk"); kv_tx = KV("tx")
P_all = sorted([p for p in ALL if p["L"] >= lo6 and p["T"] is not None and all(str(b) in kb.d for b in range(p["L"] - 3, p["Tbn"] + 4))], key=lambda p: p["L"])
SL = [p for p in P_all if p["L"] >= lo2]; OLD = [p for p in P_all if p["L"] < lo2]; NEW = [p for p in SL if p["L"] > FINDER_LAST_L]
# --- bot wallets with the block first seen
first = {}
def see(w, bn):
    w = w.lower()
    if w not in first or bn < first[w]: first[w] = bn
for h, t in kv_tx.d.items():
    if (t.get("to") or "").lower() == BOT and (t.get("input") or "")[2:10] == "c1120e3d": see(t["from"], int(t["blockNumber"], 16))
for k, b in kb.d.items():
    for t in b["txs"]:
        if (t.get("to") or "").lower() == BOT and (t.get("input") or "")[2:10] == "c1120e3d": see(t["from"], b["number"])
BW = first
print(f"bot wallets (c1120e3d senders to the router) seen: {len(BW)}; mode {'FULL (look-ahead)' if FULL else 'CAUSAL (first seen before the block)'}")
print(f"pools: last 2 h (slice, L >= {lo2}) {len(SL)}, of them launched after the finder's last pool {FINDER_LAST_L}: {len(NEW)}; the 4 h before (older) {len(OLD)}; head {D['head']} {utc(D['head_ts'])} UTC")
newest_bw_in_slice = sum(1 for w, b in BW.items() if b >= lo2)
print(f"wallets first seen inside the slice: {newest_bw_in_slice}")
def is_bw(a, bn): a = (a or "").lower(); return a in BW and (FULL or BW[a] < bn)
def kind(t):
    to = (t.get("to") or "").lower(); sel = (t.get("input") or "")[2:10]
    if to == BOT and sel == "c1120e3d": return "buy"
    if to == UR and sel == "24856bc3": return "sell"
    if to == BOT: return "router-" + sel
    return "other"
VAR = {"W0 any tx from a bot wallet (the candidate)": lambda k: True, "W1 bot-wallet buy (c1120e3d)": lambda k: k == "buy",
       "W2 bot-wallet sell (24856bc3 to the UR)": lambda k: k == "sell", "W3 bot wallet, anything else": lambda k: k not in ("buy", "sell")}
pre = {v: {} for v in VAR}; kinds = collections.Counter(); same = 0; buyer_prev = {}
for p in P_all:
    for v in VAR: pre[v][p["pid"]] = []
    tok = p["token"][2:].lower(); pid = p["pid"][2:].lower()
    buyer = (kv_tx.d.get(p["Ttx"]) or {}).get("from", "").lower(); p["buyer"] = buyer
    for bn in range(p["L"] + 1, p["Tbn"] + 1):
        b = kb.d[str(bn)]
        for i, t in enumerate(b["txs"]):
            ti = int(t["transactionIndex"], 16) if t.get("transactionIndex") else i
            if bn == p["Tbn"] and ti >= p["Tti"]: continue
            if not is_bw(t.get("from"), bn): continue
            inp = (t.get("input") or "").lower()
            if tok in inp or pid in inp: same += 1; continue
            k = kind(t); kinds[k] += 1
            if (t.get("from") or "").lower() == buyer: buyer_prev[p["pid"]] = max(buyer_prev.get(p["pid"], 0), bn)
            for v, f in VAR.items():
                if f(k): pre[v][p["pid"]].append(bn)
print(f"bot-wallet txs in blocks L+1..T ahead of the bot's buy (other pools), by kind: {dict(kinds)}; carrying this pool's token/id (excluded): {same}")
def stats(S, lab):
    n = len(S); print(f"\n==== {lab}: n {n} pools; T offset p10/50/90 {[pct([p['T'] for p in S], x) for x in (.1, .5, .9)]} min {min(p['T'] for p in S)} max {max(p['T'] for p in S)}; "
                      f"share of T within +-1 of the best fixed offset {max(sum(1 for p in S if abs(p['T'] - m) <= 1) for m in range(15, 65)) / n:.2f}")
    for v in VAR:
        dd = collections.defaultdict(set); bgh = bgn = 0; blk_d = collections.Counter(); blk_n = collections.Counter()
        for p in S:
            bs = collections.Counter(pre[v][p["pid"]])
            for bn in bs: dd[p["Tbn"] - bn].add(p["pid"])
            for bn in range(p["L"] + 4, p["Tbn"] - 4): bgn += 1; bgh += bn in bs
            for d in range(1, 21):
                if p["Tbn"] - d > p["L"]: blk_n[d] += 1; blk_d[d] += (p["Tbn"] - d) in bs
        r = bgh / bgn if bgn else 0
        cnt = [len(dd[d]) for d in range(0, 21)]
        w14 = len(set().union(*[dd[d] for d in range(1, 5)])); w12 = len(set().union(*[dd[d] for d in range(1, 3)])); exp = n * (1 - (1 - r) ** 4)
        near = []
        for p in S:
            ds = [p["Tbn"] - bn for bn in pre[v][p["pid"]] if p["Tbn"] - bn >= 1]
            near.append(min(ds) if ds else None)
        nn = [x for x in near if x is not None]
        r14 = sum(blk_d[d] for d in range(1, 5)) / max(1, sum(blk_n[d] for d in range(1, 5))); r512 = sum(blk_d[d] for d in range(5, 13)) / max(1, sum(blk_n[d] for d in range(5, 13)))
        print(f"\n {v}: background {100 * r:.1f}% of blocks (L+4..T-5); share of blocks holding one at d 1..4 {100 * r14:.1f}% vs d 5..12 {100 * r512:.1f}%")
        print("   pools with one at d = 0..20: " + " ".join(f"{x:2d}" for x in cnt))
        print(f"   any in d 1..4: {w14}/{n} ({100 * w14 / n:.0f}%), expected at the background rate {exp:.1f} ({100 * exp / n:.0f}%); any in d 1..2: {w12}/{n} ({100 * w12 / n:.0f}%); "
              f"d 1..4 vs d 5..8 vs d 9..12: {w14} / {len(set().union(*[dd[d] for d in range(5, 9)]))} / {len(set().union(*[dd[d] for d in range(9, 13)]))}")
        print(f"   the nearest one before T (d >= 1) p10/50/90 {[pct(nn, x) for x in (.1, .5, .9)] if nn else None}, none before T in {n - len(nn)} pools; "
              f"distribution {sorted(collections.Counter(min(x, 30) for x in nn).items())}")
        pos = [len([1 for bn in pre[v][p['pid']] if bn < p['Tbn']]) for p in S]
        print(f"   precursors per pool in L+1..T-1: p10/50/90 {[pct(pos, x) for x in (.1, .5, .9)]}, mean {st.mean(pos):.1f}")
    bp = [p["Tbn"] - buyer_prev[p["pid"]] for p in S if p["pid"] in buyer_prev]
    print(f"\n W4 (look-ahead, information only) the T buyer's own last tx in L+1..T: in {len(bp)}/{n} pools, d {sorted(collections.Counter(min(x, 30) for x in bp).items())}")
for S, lab in ((SL, "SLICE: the most recent 2 h"), (NEW, "NEW: slice pools launched after the finder's last pool"), (OLD, "OLDER: the 4 h before the slice")):
    stats(S, lab)
# ---------------- gains and the replay
Q = int(5 / USD * 1e18)
def gret(p, B, S_):
    sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    adds = [m for m in p["ml"] if m["dL"] > 0]
    return replay(sw, SQRT30, adds[0]["dL"] if adds else 0, B, S_, Q, 10000, 10000, None)["ret"]
LOSS = -1.0 - GAS_USD / 5
GC = {}
def g(p, B, S_):
    k = (p["pid"], B, S_)
    if k not in GC: GC[k] = gret(p, B, S_)
    return GC[k]
for S, lab in ((SL, "slice"), (OLD, "older")):
    gg = [g(p, p["Tbn"], p["Tbn"] + 1) for p in S]; gg2 = [g(p, p["Tbn"] - 2, p["Tbn"] + 1) for p in S]
    print(f"\nfront in time on the {lab} ($5 buy at the head of T, sold at the head of T+1, gas incl.), n {len(gg)}: mean {100 * st.mean(gg):.2f}% median {100 * st.median(gg):.2f}% "
          f"min {100 * min(gg):.2f}%; bought at the head of T-2 instead: mean {100 * st.mean(gg2):.2f}%")
LAGS = [3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 6, 6, 6, 9, 17, 17, 18, 23]
def outcome(p, land, lag, s=1, tie=True):
    T = p["Tbn"]
    if land > T: return "late", g(p, land, land + 1)
    if land < T and land + lag <= T: return "pulled before T", LOSS
    sell = T + s
    ok = land + lag > sell or (tie and land + lag == sell)
    if not ok: return "pulled before our sell", LOSS
    return "in time", g(p, land, max(sell, land + 1))
def run(v, S, a, k, lag, s=1, tie=True):
    res = []
    for p in S:
        fire = [bn for bn in pre[v][p["pid"]] if bn >= p["L"] + a]
        if not fire: res.append(("no trade", None, None)); continue
        land = fire[0] + k
        if lag == "emp":
            oo = [outcome(p, land, l, s, tie) for l in LAGS]
            r = st.mean(x[1] for x in oo); o = collections.Counter(x[0] for x in oo).most_common(1)[0][0]
        else:
            o, r = outcome(p, land, lag, s, tie)
        res.append((o, r, p["Tbn"] - fire[0]))
    return res
def summ(res):
    rr = [r for _, r, _ in res if r is not None]; c = collections.Counter(o for o, _, _ in res); return c, rr
V0 = "W0 any tx from a bot wallet (the candidate)"
print("\nRULE REPLAY. W0, arm at L+a, fire on the first precursor at b >= L+a, buy lands b+k; sell lands T+1 (s 1); pull at landing + lag; tie counted for us.")
for S, lab in ((SL, "SLICE 2 h"), (NEW, "NEW only"), (OLD, "OLDER 4 h")):
    print(f"\n -- {lab} (n {len(S)}): a | lag 3 k1 | lag 3 k2 | lag 4 k1 | lag 4 k2 | empirical lag mix k1 | k2   (trades, in time, pulled, late, mean %)")
    for a in range(4, 62, 4):
        line = f"  a {a:2d}"
        for lag, k in ((3, 1), (3, 2), (4, 1), (4, 2), ("emp", 1), ("emp", 2)):
            c, rr = summ(run(V0, S, a, k, lag))
            m = st.mean(rr) if rr else 0
            line += f" | {len(rr):2d} in{c['in time']:2d} pl{c['pulled before T'] + c['pulled before our sell']:2d} lt{c['late']:2d} {100 * m:+6.1f}%"
        print(line)
# hindsight: the best arm offset per lag/k on the OLDER set, tested on the slice (out of sample), and the slice's own best (in sample)
print("\nBEST ARM OFFSET: picked on the older 4 h, tested on the slice; and the slice's own hindsight best (>= 5 trades)")
for v in VAR:
    for lag in (3, 4, "emp", 9):
        for k in (1, 2):
            def best(S):
                bb = None
                for a in range(4, 62):
                    c, rr = summ(run(v, S, a, k, lag))
                    if len(rr) < 5: continue
                    m = st.mean(rr)
                    if bb is None or m > bb[1]: bb = (a, m, len(rr), dict(c))
                return bb
            bo = best(OLD); bs = best(SL)
            if bo is None or bs is None: continue
            c, rr = summ(run(v, SL, bo[0], k, lag))
            print(f"  {v[:3]} lag {lag!s:>3} k {k}: older best a {bo[0]} ({100 * bo[1]:+.1f}% over {bo[2]}) -> slice {100 * st.mean(rr) if rr else 0:+.1f}% over {len(rr)} "
                  f"{dict(c)} ${5 * (st.mean(rr) if rr else 0):+.2f} a trade | slice in-sample best a {bs[0]} {100 * bs[1]:+.1f}% over {bs[2]} {bs[3]}")
# the optimistic same-block sell (s = 0) and the lead of fires
print("\nW0 with the optimistic same-block sell (s 0: our sell lands in T's block right behind the bot's buy), slice:")
for a in (4, 20, 30, 40):
    for lag in (3, 4, "emp"):
        for k in (1, 2):
            res = run(V0, SL, a, k, lag, s=0); c, rr = summ(res)
            leads = sorted(d for o, _, d in res if d is not None)
            print(f"  a {a:2d} lag {lag!s:>3} k {k}: {len(rr):2d} trades {dict(c)} mean {100 * st.mean(rr) if rr else 0:+6.1f}% ${5 * st.mean(rr) if rr else 0:+.2f} a trade; "
                  f"fire lead T-b p10/50/90 {[pct(leads, x) for x in (.1, .5, .9)] if leads else None}; lead in 1..2 (k1) {sum(1 for x in leads if 1 <= x <= 2)}")
print("\nW0 per-pool distribution at fixed arm offsets (no hindsight), slice, sell T+1, tie ours:")
for a in (4, 20, 30, 40):
    for lag in (3, 4, "emp"):
        for k in (1, 2):
            res = run(V0, SL, a, k, lag); c, rr = summ(res)
            if not rr: continue
            leads = sorted(d for o, _, d in res if d is not None)
            print(f"  a {a:2d} lag {lag!s:>3} k {k}: {len(rr):2d} trades {dict(c)}; mean {100 * st.mean(rr):+6.1f}% (${5 * st.mean(rr):+.2f} a trade, ${5 * sum(rr):+.2f} in all); "
                  f"p10/50/90 {[round(100 * pct(rr, x), 1) for x in (.1, .5, .9)]}%; wins {sum(1 for x in rr if x > 0)}; fire lead T-b p10/50/90 {[pct(leads, x) for x in (.1, .5, .9)]}")
pickle.dump({"pre": pre, "SL": [p["pid"] for p in SL], "OLD": [p["pid"] for p in OLD], "NEW": [p["pid"] for p in NEW], "BW": BW}, open("s4_rule%s.pkl" % ("_full" if FULL else ""), "wb"))
