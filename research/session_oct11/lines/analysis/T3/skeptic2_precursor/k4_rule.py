"""Stage 4: candidate 1 re-measured on the most recent 2 hours of 3.0 pools, from whole blocks (every transaction, failed ones included).
Candidate: 'a transaction to the bot router 0x1cbaf24d (any selector, any other pool), seen in the feed: buy so that it lands 1-2 blocks later.'
Precursor = a tx to 0x1cbaf24d whose token (c1120e3d word 2, a0f7978d word 0) is not this pool's token, in blocks [L+1, T] (in T's block only
ahead of the bot's buy). d = T - (precursor block). Variants: V0 the candidate; V1 c1120e3d only; V2 a0f7978d only; V3 c1120e3d in another
3.0 pool; V4 another 3.0 pool's first bot buy (its T).
Replay of the rule: armed at L+a, fire on the first precursor at block b >= L+a; our buy lands at b+k (k = 1 or 2). Reaction (k2: buys before
T pulled 3..23 blocks later, min 3, median 4; our own probe 9): pull at landing + lag.
  landing < T and landing + lag <= T: pulled before the bot buys: -100%;
  landing <= T: the bot buys at T (ours ahead of it in T's block, the best case), our sell (sent on seeing the bot's buy) lands at T+1;
    survives iff landing + lag > T+1 (strict) or >= T+1 (tie counted for us); else -100%; gain from the integer replay (buy head of landing,
    sell head of T+1, every other swap between re-applied);
  landing > T: late, a buy behind the bot sold the next block (replayed);
  no precursor in [L+a, T]: no trade.
$5 stake (0.001946 ETH at $2,570), gas $0.02 a trade (R's figures)."""
import pickle, sys, os, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from lib import *
from common import replay, GAS_USD, USD
os.chdir(HERE)
FINDER_HEAD = 86158232                     # the precursor angle's stage-1 head (its pools all launched before it)
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2
D = pickle.load(open("k2_parsed.pkl", "rb")); lo = D["head"] - int(hours * 3600 * D["bps"])
ALL = D["pools"]; P = [p for p in ALL if p["L"] >= lo and p["T"] is not None]
kb = KV("blk")
tok30 = {p["token"] for p in ALL}; Tbn_of = {p["token"]: p["Ttx"] for p in ALL if p["Ttx"]}
Q = int(5 / USD * 1e18)
def tok_of(t):
    inp = t.get("input") or ""; sel = inp[2:10]
    if sel == "c1120e3d" and len(inp) >= 10 + 64 * 3: return "0x" + inp[10 + 64 * 2 + 24: 10 + 64 * 3]
    if sel == "a0f7978d" and len(inp) >= 10 + 64: return "0x" + inp[10 + 24: 10 + 64]
    return None
VAR = {"V0 any tx to the bot router, other pool": lambda t, tok, sel: True,
       "V1 c1120e3d (bot buy) other pool": lambda t, tok, sel: sel == "c1120e3d",
       "V2 a0f7978d (pull) other pool": lambda t, tok, sel: sel == "a0f7978d",
       "V3 c1120e3d in another 3.0 pool": lambda t, tok, sel: sel == "c1120e3d" and tok in tok30,
       "V4 another 3.0 pool's first bot buy": lambda t, tok, sel: t["hash"] in set(Tbn_of.values())}
same_pool = collections.Counter(); selc = collections.Counter(); per_block = []
pre = {v: {} for v in VAR}            # variant -> pid -> sorted list of (bn, ti)
for p in P:
    for v in VAR: pre[v][p["pid"]] = []
    for bn in range(p["L"] + 1, p["Tbn"] + 1):
        b = kb.d[str(bn)]; nb = 0
        for i, t in enumerate(b["txs"]):
            if (t.get("to") or "").lower() != BOT: continue
            ti = int(t["transactionIndex"], 16) if t.get("transactionIndex") else i
            if bn == p["Tbn"] and ti >= p["Tti"]: continue
            tok = tok_of(t); sel = (t.get("input") or "")[2:10]
            if tok == p["token"]: same_pool[sel] += 1; continue
            selc[sel] += 1; nb += 1
            for v, f in VAR.items():
                if f(t, tok, sel): pre[v][p["pid"]].append((bn, ti))
        if bn < p["Tbn"]: per_block.append(nb)
n = len(P); new = [p for p in P if p["L"] > FINDER_HEAD]
print(f"slice: 3.0 pools with a bot buy launched from block {lo} to the head {D['head']} ({hours:g} h): {n}; launched after the finder's head "
      f"{FINDER_HEAD}: {len(new)}")
Ts = [p["T"] for p in P]
print(f"T offset p10/25/50/75/90 {[pct(Ts, x) for x in (.1, .25, .5, .75, .9)]} min {min(Ts)} max {max(Ts)}; share within +-1 of the best fixed offset "
      f"{max(sum(1 for x in Ts if abs(x - m) <= 1) for m in range(15, 65)) / n:.2f}")
print(f"txs to the bot router in blocks L+1..T (ahead of the bot's buy), by selector: {dict(selc)}; in this same pool (excluded): {dict(same_pool)}")
print(f"blocks L+1..T-1: {len(per_block)}, with >= 1 router tx (other pool): {sum(1 for x in per_block if x)} ({100 * sum(1 for x in per_block if x) / len(per_block):.1f}%), "
      f"router txs per block {sum(per_block) / len(per_block):.3f}")
for v in VAR:
    dd = collections.defaultdict(set); bgh = 0; bgn = 0
    for p in P:
        for bn, ti in pre[v][p["pid"]]: dd[p["Tbn"] - bn].add(p["pid"])
        # background: blocks L+4..T-5 holding the precursor
        bs = {bn for bn, _ in pre[v][p["pid"]]}
        for bn in range(p["L"] + 4, p["Tbn"] - 4): bgn += 1; bgh += bn in bs
    r = bgh / bgn if bgn else 0
    cnt = [len(dd[d]) for d in range(0, 21)]
    w14 = len(set().union(*[dd[d] for d in range(1, 5)])); exp = n * (1 - (1 - r) ** 4)
    near = []
    for p in P:
        ds = [p["Tbn"] - bn for bn, _ in pre[v][p["pid"]] if p["Tbn"] - bn >= 1]
        near.append(min(ds) if ds else None)
    nn = [x for x in near if x is not None]
    print(f"\n{v}: background {100 * r:.1f}% of blocks (L+4..T-5); pools with one at d = 0..20 blocks before T:\n   " + " ".join(f"{x:2d}" for x in cnt))
    print(f"   any in d 1..4: {w14}/{n} ({100 * w14 / n:.0f}%), expected at the background rate {exp:.1f} ({100 * exp / n:.0f}%); "
          f"in d 1..4 vs the mean of the same-width windows d 5..8 and 9..12: {w14} vs "
          f"{(len(set().union(*[dd[d] for d in range(5, 9)])) + len(set().union(*[dd[d] for d in range(9, 13)]))) / 2:.1f}")
    print(f"   the nearest one before T (d >= 1), p10/50/90 {[pct(nn, x) for x in (.1, .5, .9)] if nn else None}, none before T in {n - len(nn)} pools; "
          f"distribution {sorted(collections.Counter(min(x, 30) for x in nn).items())}")
    pos = [len([1 for bn, _ in pre[v][p['pid']] if bn < p['Tbn']]) for p in P]
    print(f"   precursors per pool in L+1..T-1: p10/50/90 {[pct(pos, x) for x in (.1, .5, .9)]}, mean {st.mean(pos):.1f}")
# gains
gain = {}
def gret(p, B, S):
    sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    adds = [m for m in p["ml"] if m["dL"] > 0]
    return replay(sw, SQRT30, adds[0]["dL"] if adds else 0, B, S, Q, 10000, 10000, None)["ret"]
for p in P:
    gain[p["pid"]] = gret(p, p["Tbn"], p["Tbn"] + 1)
g = [x for x in gain.values() if x is not None]
print(f"\nfront in time ($5 buy at the head of T, sold at the head of T+1, gas incl.), n {len(g)}: mean {100 * st.mean(g):.2f}% median {100 * st.median(g):.2f}% "
      f"min {100 * min(g):.2f}% max {100 * max(g):.2f}%")
LOSS = -1.0 - GAS_USD / 5
def outcome(p, land, lag, tie):
    T = p["Tbn"]
    if land > T: return "late", gret(p, land, land + 1)
    if land < T and land + lag <= T: return "pulled before T", LOSS
    ok = land + lag > T + 1 or (tie and land + lag == T + 1)
    if not ok: return "pulled before our sell", LOSS
    return "in time", gret(p, land, T + 1)
def run(v, a, k, lag, tie, S=None):
    res = []; S = S or P
    for p in S:
        fire = [bn for bn, _ in pre[v][p["pid"]] if bn >= p["L"] + a]
        if not fire: res.append(("no trade", None, None)); continue
        land = fire[0] + k
        o, r = outcome(p, land, lag, tie); res.append((o, r, p["Tbn"] - fire[0]))
    return res
def summ(res):
    rr = [r for _, r, _ in res if r is not None]
    c = collections.Counter(o for o, _, _ in res)
    return c, rr
print("\nRULE REPLAY on the slice (n %d). Columns: arm offset a; per lag (pull at our landing + lag) and landing k: trades, in time, "
      "pulled, late, mean %% a trade, $ a trade at $5 (tie: pull and our sell in the same block counted for us)" % n)
for v in ("V0 any tx to the bot router, other pool", "V1 c1120e3d (bot buy) other pool", "V4 another 3.0 pool's first bot buy"):
    print(f"\n {v}")
    best = {}
    for a in range(4, 62, 2):
        line = f"  a {a:2d}"
        for lag in (3, 4, 9):
            for k in (1, 2):
                c, rr = summ(run(v, a, k, lag, True))
                m = st.mean(rr) if rr else 0
                if (lag, k) not in best or m > best[(lag, k)][1]: best[(lag, k)] = (a, m, len(rr))
                if lag in (3, 4) or k == 1:
                    line += f" | L{lag}k{k} {len(rr):2d} in{c['in time']:2d} pull{c['pulled before T'] + c['pulled before our sell']:2d} late{c['late']:2d} {100 * m:+7.1f}%"
        print(line)
    print("  best arm offset in hindsight (on the slice itself): " + "; ".join(f"lag {l} k {k}: a {b[0]} mean {100 * b[1]:+.1f}% over {b[2]} trades (${5 * b[1]:+.2f})" for (l, k), b in sorted(best.items())))
# the outcome distribution at the hindsight-best a for V0, lag 3/4, k 1/2, strict and lenient tie
print("\nV0 outcome detail at each lag's hindsight-best arm offset with at least 5 trades (strict tie = the pull wins a same-block tie):")
for lag in (3, 4, 9):
    for k in (1, 2):
        for tie in (True, False):
            bestm = None
            for a in range(4, 62):
                c, rr = summ(run("V0 any tx to the bot router, other pool", a, k, lag, tie))
                m = st.mean(rr) if len(rr) >= 5 else -9
                if bestm is None or m > bestm[1]: bestm = (a, m)
            res = run("V0 any tx to the bot router, other pool", bestm[0], k, lag, tie); c, rr = summ(res)
            leads = sorted(d for o, _, d in res if d is not None)
            print(f"  lag {lag} k {k} tie {'ours' if tie else 'pull'}: a {bestm[0]}: {dict(c)}; mean {100 * st.mean(rr):+.1f}% median {100 * st.median(rr):+.1f}% "
                  f"win {sum(1 for x in rr if x > 0)}/{len(rr)}; ${5 * st.mean(rr):+.2f} a trade, ${5 * sum(rr):+.2f} in all; fire lead d=T-b p10/50/90 "
                  f"{[pct(leads, x) for x in (.1, .5, .9)]}")
# the same on the pools launched after the finder's head only (strictly new pools)
print(f"\nstrictly new pools only (n {len(new)}), V0, every arm offset a: best mean per lag/k")
for lag in (3, 4):
    for k in (1, 2):
        b = max(((a,) + (lambda c_rr: (st.mean(c_rr[1]) if c_rr[1] else -9, len(c_rr[1]), c_rr[0]))(summ(run("V0 any tx to the bot router, other pool", a, k, lag, True, new))) for a in range(4, 62)), key=lambda x: x[1])
        print(f"  lag {lag} k {k}: best a {b[0]}: mean {100 * b[1]:+.1f}% over {b[2]} trades {dict(b[3])}")
pickle.dump({"P": [p["pid"] for p in P], "pre": pre, "gain": gain}, open("k4_rule.pkl", "wb"))

print("\nV0 at fixed arm offsets (no hindsight): a $5 front per pool, distribution of the return")
for a in (4, 20, 30):
    for lag in (3, 4):
        for k in (1, 2):
            for S, lab in ((P, "slice"), (new, "new only")):
                res = run("V0 any tx to the bot router, other pool", a, k, lag, True, S); c, rr = summ(res)
                if not rr: continue
                print(f"  a {a:2d} lag {lag} k {k} {lab:8s}: {len(rr):2d} trades {dict(c)}; mean {100 * st.mean(rr):+6.1f}% (${5 * st.mean(rr):+.2f} a trade, ${5 * sum(rr):+.2f} in all); "
                      f"p10/50/90 {[round(100 * pct(rr, x), 1) for x in (.1, .5, .9)]}%; wins {sum(1 for x in rr if x > 0)}")
