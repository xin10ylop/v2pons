"""Stage 5: candidate 5 measured on this slice. Every 1,444-byte call to the PositionManager 0x58daec31 (any value, any line, any status,
from the whole blocks of stage 3) at d = 0..12 blocks before T (d = 0: in T's block ahead of the bot's tx); its hit rate in d 1..4, the lead
distribution, against the background (blocks L+10..T-13 of the same pools, and the whole slice from the Initialize stream); its precision
(of the launches seen while a pool is waiting for T, the share followed by T 1..4 blocks later).
Then an engine that follows it: a pool is armed from L+A until it sees the bot's buy (or a pull, or L+65); on the first 1,444-byte call seen
in that window at block b it buys, landing at x = b+k (k = 1 or 2). The operator's reaction: a pull at x + lag (lag = the minimum pre-T lag
3, the median pre-T lag, 9 = the overall median; 'none' = no reaction, a counterfactual). Our sell, sent on seeing the bot's buy, lands at
T+1 (base) or T (optimistic); a pull in the sell's block or earlier = -100%. x == T counts half as a front (ahead of the bot) and half as
late (behind it). Late buys (x > T) are sold k blocks later. Prices from the R study's integer replay (analysis/R/common.py), $5 stake,
fee 1% each way, gas $0.02 a round trip."""
import pickle, json, collections, sys, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD, NEW30
from lib import *
LAGMED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
D = pickle.load(open("parsed.pkl", "rb")); S = json.load(open("stream.json"))
kb = KV("blk")
P = sorted(D["pools"], key=lambda p: p["L"])
def calls(bn):
    b = kb.d.get(str(bn))
    if b is None: return None
    return [dict(bn=bn, ti=int(t["transactionIndex"], 16), frm=t["from"].lower(), v=int(t["value"], 16), tx=t["hash"])
            for t in b["txs"] if (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444]
t0, t1 = D["t0"], D["t1"]; bps = (D["end"] - D["start"]) / (t1 - t0)
def ts_of(bn): return t0 + (bn - D["start"]) / bps
# ---- coverage / cross-check against the Initialize stream
init_set = {(s["bn"], s["ti"]) for s in S["stream"]}
scanned = sorted(set(int(k) for k in kb.d))
blk_calls = [c for bn in scanned for c in (calls(bn) or [])]
no_init = [c for c in blk_calls if (c["bn"], c["ti"]) not in init_set]
print(f"slice {utc(t0)} -> {utc(t1)} UTC, {bps:.2f} blocks/s; 3.0 pools {len(P)}, with a bot buy {sum(1 for p in P if p['T'] is not None)}")
print(f"whole blocks scanned {len(scanned)}; 1444-byte PositionManager calls in them {len(blk_calls)}, of which without an Initialize (reverted or not a launch) {len(no_init)}")
lam_slice = len({s['bn'] for s in S['stream']}) / (D["end"] - D["start"] + 1)
print(f"Initialize-bearing 1444-byte launches in the whole slice: {len(S['stream'])} in {D['end']-D['start']+1} blocks = {lam_slice:.5f} of blocks hold one; "
      f"by value: {collections.Counter(s['line'] if s['line'] in ('3.0','2.433','v5','v9.33333','v40') else 'other' for s in S['stream']).most_common()}")
# ---- hit rate on pools with T and the whole window
full = []
for p in P:
    if p["T"] is None: continue
    rng = range(p["L"] + 1, p["Tbn"] + 4)
    if all(str(b) in kb.d for b in rng): full.append(p)
print(f"\npools with a bot buy and every block L+1..T+3: {len(full)}; T p10/50/90 {pct([p['T'] for p in full],.1)}/{pct([p['T'] for p in full],.5)}/{pct([p['T'] for p in full],.9)}")
def dset(p, kind="all"):
    out = collections.defaultdict(list)
    for d in range(0, 13):
        bn = p["Tbn"] - d
        if bn <= p["L"]: continue
        for c in calls(bn) or []:
            if d == 0 and c["ti"] > p["Tti"]: continue
            if kind == "3.0" and c["v"] != 3 * 10 ** 18: continue
            if kind == "not3.0" and c["v"] == 3 * 10 ** 18: continue
            out[d].append(c)
    return out
def bgrate(Pset, kind="all"):
    nb = hit = 0
    for p in Pset:
        for bn in range(p["L"] + 1, p["Tbn"] - 12):
            cs = calls(bn) or []
            if kind == "3.0": cs = [c for c in cs if c["v"] == 3 * 10 ** 18]
            if kind == "not3.0": cs = [c for c in cs if c["v"] != 3 * 10 ** 18]
            nb += 1; hit += 1 if cs else 0
    return hit / nb if nb else None, nb
def table(Pset, label, kind="all"):
    if not Pset: return
    cnt = [0] * 13; hits = []; leads = []
    for p in Pset:
        ds = dset(p, kind)
        for d in range(13):
            if ds.get(d): cnt[d] += 1
        w = [d for d in range(1, 5) if ds.get(d)]
        if w: hits.append(p); leads.append(min(w))
    w58 = sum(1 for p in Pset if any(dset(p, kind).get(d) for d in range(5, 9)))
    w912 = sum(1 for p in Pset if any(dset(p, kind).get(d) for d in range(9, 13)))
    r, nb = bgrate(Pset, kind)
    r = r if r is not None else lam_slice
    exp4 = len(Pset) * (1 - (1 - r) ** 4)
    print(f"  {label:44s} n {len(Pset):3d}  pools with a call at d=0..12: " + " ".join(f"{x:2d}" for x in cnt) +
          f" | d1-4: {len(hits)} ({100*len(hits)/len(Pset):.1f}%), expected at background {exp4:.1f} (bg {r if r is None else round(r,4)}/block over {nb} blocks); "
          f"nearest lead d1..4: {dict(sorted(collections.Counter(leads).items()))}; same-width windows d5-8 {w58}, d9-12 {w912}")
    return hits, leads
print("\n== hit rate: pools with a 1444-byte call d blocks before T (d=0 = in T's block ahead of the bot's tx)")
new = [p for p in full if ts_of(p["L"]) >= NEW30]; old = [p for p in full if ts_of(p["L"]) < NEW30]
n = len(full); thirds = [full[: n // 3], full[n // 3: 2 * n // 3], full[2 * n // 3:]]
res = table(full, "whole slice, any 1444-byte call")
table(full, "whole slice, 3.0-valued launches only", "3.0")
table(full, "whole slice, other values only", "not3.0")
table(old, "old regime (L before 04:22 UTC Oct 11)")
table(new, "new regime (L from 04:22 UTC Oct 11)")
for i, th in enumerate(thirds): table(th, f"third {i+1} (L {utc(ts_of(th[0]['L']))}..{utc(ts_of(th[-1]['L']))})")
# ---- the launch stream's clustering (why a launch sits near T by chance): gaps between consecutive 1444-byte launches, per regime
print("\n== gaps between consecutive 1444-byte launches (Initialize stream), blocks")
st_ = sorted(S["stream"], key=lambda s: (s["bn"], s["ti"]))
for reg, sel in (("old", lambda bn: ts_of(bn) < NEW30), ("new", lambda bn: ts_of(bn) >= NEW30)):
    X = [s["bn"] for s in st_ if sel(s["bn"])]
    g = [b - a for a, b in zip(X, X[1:])]
    nblk = (max(X) - min(X)) if X else 0
    print(f"  {reg}: launches {len(X)} ({len(X)/((nblk or 1)/bps/3600):.1f}/h); gap p10/25/50/75/90 {pct(g,.1)}/{pct(g,.25)}/{pct(g,.5)}/{pct(g,.75)}/{pct(g,.9)}; "
          f"gaps <= 4 blocks {sum(1 for x in g if x <= 4)}, <= 60 {sum(1 for x in g if x <= 60)} of {len(g)}")
    X3 = [s["bn"] for s in st_ if sel(s["bn"]) and s["line"] == "3.0"]; g3 = [b - a for a, b in zip(X3, X3[1:])]
    print(f"     3.0 only: {len(X3)}; gap p10/25/50/75/90 {pct(g3,.1)}/{pct(g3,.25)}/{pct(g3,.5)}/{pct(g3,.75)}/{pct(g3,.9)}; next 3.0 launch within L+1..L+60 of a 3.0 launch: {sum(1 for x in g3 if x <= 60)} of {len(g3)}")
# ---- precision: of the 1444-byte calls seen while a pool waits for T, how many are followed by T 1..4 blocks later
print("\n== precision: (pool, call) pairs with the pool armed at the call (L+A <= b, b before T and before any pull, b <= L+65)")
def armed_end(p):
    e = p["L"] + 65
    if p["Tbn"] is not None: e = min(e, p["Tbn"])
    if p["pullbn"] is not None: e = min(e, p["pullbn"] - 1)
    return e
def complete(p, A):
    return all(str(b) in kb.d for b in range(p["L"] + A, armed_end(p) + 1))
NEWP = [p for p in P if ts_of(p["L"]) >= NEW30]
print(f"   (current regime only: pools launched from 04:22 UTC Oct 11, n {len(NEWP)}; the old regime's T sits at L+8..10)")
for A in (10, 18, 25, 30, 35, 40):
    pairs = good = good_d23 = 0; pools_used = 0
    for p in NEWP:
        if not complete(p, A): continue
        pools_used += 1
        for bn in range(p["L"] + A, armed_end(p) + 1):
            for c in calls(bn) or []:
                if p["Tbn"] is not None and bn == p["Tbn"] and c["ti"] > p["Tti"]: continue
                pairs += 1
                if p["Tbn"] is not None and 1 <= p["Tbn"] - bn <= 4: good += 1
                if p["Tbn"] is not None and 2 <= p["Tbn"] - bn <= 3: good_d23 += 1
    print(f"  A={A:2d}: pools {pools_used}, (pool, call) pairs {pairs}, followed by T at +1..+4: {good} ({100*good/max(1,pairs):.1f}%), at +2..+3: {good_d23} ({100*good_d23/max(1,pairs):.1f}%)")
# ---- the engine replay
q = int(5 / USD * 1e18)
def sw_of(p): return [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
def L0(p):
    adds = [m for m in p["ml"] if m["dL"] > 0]; return adds[0]["dL"] if adds else 0
LOSS = -1.0 - GAS_USD / 5
def trade(p, x, k, lag, sell_at):
    """returns (kind, ret)"""
    if p["Tbn"] is None:
        return "no bot buy", LOSS
    T = p["Tbn"]
    def front():
        pull = None if lag is None else x + lag
        if p["pullbn"] is not None and p["pullbn"] >= x: pull = p["pullbn"] if pull is None else min(pull, p["pullbn"])
        sb = T + 1 if sell_at == "T+1" else T
        if pull is not None and pull <= max(sb, T):   # a pull at or before our sell (or before the bot's buy) -> -100%
            return "front pulled", LOSS
        r = replay(sw_of(p), SQRT30, L0(p), x, T + 1, q, 10000, 10000, None)["ret"]
        return "front ok", r
    def late():
        r = replay(sw_of(p), SQRT30, L0(p), x, x + k, q, 10000, 10000, None)["ret"]
        return "late", r
    if x < T: return front()
    if x == T:
        a, ra = front(); b, rb = late(); return "at T (half/half)", (ra + rb) / 2
    return late()
def engine(Pset, A, k, lag, sell_at="T+1"):
    out = collections.Counter(); rets = []; leads = []
    for p in Pset:
        if not complete(p, A): out["incomplete"] += 1; continue
        fire = None
        for bn in range(p["L"] + A, armed_end(p) + 1):
            cs = [c for c in (calls(bn) or []) if not (p["Tbn"] is not None and bn == p["Tbn"] and c["ti"] > p["Tti"])]
            if cs: fire = bn; break
        if fire is None: out["no fire"] += 1; continue
        kind, r = trade(p, fire + k, k, lag, sell_at)
        out[kind] += 1; rets.append(r)
        if p["Tbn"] is not None: leads.append(p["Tbn"] - fire)
    return out, rets, leads
hours = (t1 - NEW30) / 3600
print(f"\n== engine following the rule (first 1444-byte call while armed -> buy lands k blocks later), $5 stake; current regime: {len(NEWP)} pools in {hours:.1f} h")
print("   lag = blocks from our buy to the operator's pull ('none' = no reaction). Sell lands at T+1 unless noted.")
best = None
for A in (10, 18, 25, 30, 35, 40, 45):
    for k in (1, 2):
        for lag in (3, 4, 5, 6, 9, None):
            out, rets, leads = engine(NEWP, A, k, lag)
            if not rets: continue
            m = st.mean(rets); usd = [5 * r for r in rets]
            tag = f"A={A:2d} k={k} lag={lag if lag is not None else 'none':>4}"
            print(f"  {tag}: trades {len(rets):3d} ({len(rets)/hours:4.1f}/h)  mean {100*m:7.2f}%  median {100*st.median(rets):7.2f}%  win {sum(1 for r in rets if r > 0)/len(rets):.2f}  "
                  f"${st.mean(usd):+.2f}/trade  ${sum(usd)/hours:+7.2f}/h | " + ", ".join(f"{a} {b}" for a, b in sorted(out.items())))
            if lag == 3 and (best is None or m > best[0]): best = (m, A, k)
print(f"\nbest (A, k) under lag 3: A={best[1]} k={best[2]} mean {100*best[0]:.2f}%")
out, rets, leads = engine(NEWP, 25, 2, 3)
print("lead d = T - (block of the triggering call) for the fired pools that had a bot buy, A=25 k=2:", sorted(collections.Counter(leads).items())[:30])
# ---- optimistic variant: sell lands at T
print("\n== optimistic: our sell lands in T itself (behind the bot's buy)")
for A in (18, 25, 35):
    for k in (1, 2):
        for lag in (3, 5):
            out, rets, _ = engine(NEWP, A, k, lag, "T")
            m = st.mean(rets); usd = [5 * r for r in rets]
            print(f"  A={A:2d} k={k} lag={lag}: trades {len(rets)} mean {100*m:7.2f}% ${st.mean(usd):+.2f}/trade ${sum(usd)/hours:+.2f}/h | " + ", ".join(f"{a} {b}" for a, b in sorted(out.items())))
# ---- oracle upper bound: an engine that fires ONLY on the calls that really were 1..4 blocks before T (impossible to know in advance)
print("\n== oracle bound: fire only on the hits (a call at d 1..4 before T), k=1 or 2, lag 3 / median; T+1 sell")
for k in (1, 2):
    for lag in (3, 5, None):
        rets = []; kinds = collections.Counter()
        for p in [p for p in full if ts_of(p["L"]) >= NEW30]:
            ds = dset(p)
            w = [d for d in range(4, 0, -1) if ds.get(d)]
            if not w: continue
            b = p["Tbn"] - w[0]
            kind, r = trade(p, b + k, k, lag, "T+1"); kinds[kind] += 1; rets.append(r)
        if rets: print(f"  k={k} lag={lag}: trades {len(rets)} of {sum(1 for p in full if ts_of(p["L"]) >= NEW30)} pools; mean {100*st.mean(rets):.2f}% ${5*st.mean(rets):+.2f}/trade, ${5*sum(rets)/hours:+.2f}/h | {dict(kinds)}")
