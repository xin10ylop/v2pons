"""Stage 6: (a) the d-histogram of candidate 1 (V0: any tx to the bot router, other pool) on the 2 hours BEFORE the slice too; (b) the one
setting that looked positive on the slice only in hindsight and only with a 9-block lag (armed at L+45/46, which simply trades the pools with
a late T), replayed on those older pools; (c) the reaction drawn from the measured pre-T lag distribution (k2: every outside non-dust buy
before T in 9 h, 23 pools) instead of a single lag: expected return per trade = gain x P(lag survives) - 100.4% x P(pulled)."""
import pickle, sys, os, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from lib import *
from common import replay, USD
os.chdir(HERE)
D = pickle.load(open("k2_parsed.pkl", "rb")); kb = KV("blk"); bps = D["bps"]
h2 = D["head"] - int(2 * 3600 * bps); h4 = D["head"] - int(4 * 3600 * bps)
ALLP = [p for p in D["pools"] if p["T"] is not None]
SL = [p for p in ALLP if p["L"] >= h2]; OLD = [p for p in ALLP if h4 <= p["L"] < h2]
rows = pickle.load(open("k2_reaction_rows.pkl", "rb"))
first = {}
for r in rows:
    if r["when"] == "before T" and not r["dust"]: first.setdefault(r["pid"], r)
LAGS = sorted(r["lag"] for r in first.values() if r["lag"] is not None)
print(f"slice {len(SL)} pools (L >= {h2}); older {len(OLD)} pools ({h4} <= L < {h2}); measured pre-T lags (n {len(LAGS)}): {LAGS}")
Q = int(5 / USD * 1e18); LOSS = -1.0 - 0.02 / 5
def tok_of(t):
    inp = t.get("input") or ""; sel = inp[2:10]
    if sel == "c1120e3d" and len(inp) >= 10 + 64 * 3: return "0x" + inp[10 + 64 * 2 + 24: 10 + 64 * 3]
    if sel == "a0f7978d" and len(inp) >= 10 + 64: return "0x" + inp[10 + 24: 10 + 64]
    return None
def precursors(p):
    out = []
    for bn in range(p["L"] + 1, p["Tbn"] + 1):
        for i, t in enumerate(kb.d[str(bn)]["txs"]):
            if (t.get("to") or "").lower() != BOT: continue
            ti = int(t["transactionIndex"], 16) if t.get("transactionIndex") else i
            if bn == p["Tbn"] and ti >= p["Tti"]: continue
            if tok_of(t) == p["token"]: continue
            out.append(bn)
    return out
def gret(p, B, S):
    sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    adds = [m for m in p["ml"] if m["dL"] > 0]
    return replay(sw, SQRT30, adds[0]["dL"] if adds else 0, B, S, Q, 10000, 10000, None)["ret"]
for p in SL + OLD: p["pre"] = precursors(p)
for S, lab in ((OLD, "older 2 h"), (SL, "slice")):
    dd = collections.defaultdict(set)
    for p in S:
        for bn in p["pre"]: dd[p["Tbn"] - bn].add(p["pid"])
    w14 = len(set().union(*[dd[d] for d in range(1, 5)])); w58 = len(set().union(*[dd[d] for d in range(5, 9)])); w912 = len(set().union(*[dd[d] for d in range(9, 13)]))
    print(f"\n{lab}: pools with a V0 precursor at d = 0..20: " + " ".join(f"{len(dd[d]):2d}" for d in range(21)))
    print(f"   any in d 1..4 {w14}/{len(S)} ({100 * w14 / len(S):.0f}%), d 5..8 {w58}, d 9..12 {w912}")
def trade(p, a, k, lag, tie=True):
    f = [bn for bn in p["pre"] if bn >= p["L"] + a]
    if not f: return None
    land = f[0] + k; T = p["Tbn"]
    if land > T: return ("late", gret(p, land, land + 1))
    if land < T and land + lag <= T: return ("pulled", LOSS)
    if land + lag > T + 1 or (tie and land + lag == T + 1): return ("in time", gret(p, land, T + 1))
    return ("pulled", LOSS)
print("\n(b) the hindsight settings, on the slice (where they were picked) and on the older pools (out of sample):")
for a in (45, 46):
    for lag in (9, 4, 3):
        for k in (1, 2):
            for S, lab in ((SL, "slice"), (OLD, "older")):
                rr = [x for x in (trade(p, a, k, lag) for p in S) if x]
                v = [r for _, r in rr]
                print(f"  a {a} lag {lag} k {k} {lab:6s}: {len(v):2d} trades {dict(collections.Counter(o for o, _ in rr))} mean {100 * st.mean(v) if v else 0:+6.1f}% "
                      f"${5 * sum(v):+.2f} in all")
print("\n(c) the reaction drawn from the measured pre-T lags (each trade's outcome averaged over the 23 lags), V0, k = 1 and 2, tie counted for us:")
for S, lab in ((SL, "slice"), (OLD, "older"), (SL + OLD, "both")):
    for k in (1, 2):
        line = f"  {lab:6s} k {k}:"
        for a in (4, 10, 20, 30, 40, 45):
            ev = []
            for p in S:
                f = [bn for bn in p["pre"] if bn >= p["L"] + a]
                if not f: continue
                land = f[0] + k; T = p["Tbn"]
                if land > T: ev.append(gret(p, land, land + 1)); continue
                g = gret(p, land, T + 1)
                surv = sum(1 for l in LAGS if land + l >= T + 1 and not (land < T and land + l <= T)) / len(LAGS)
                ev.append(surv * g + (1 - surv) * LOSS)
            line += f" | a {a}: {len(ev)} tr {100 * st.mean(ev) if ev else 0:+6.1f}% (${5 * st.mean(ev) if ev else 0:+.2f})"
        print(line)
