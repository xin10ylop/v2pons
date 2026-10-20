"""Stage 5: the precursor angle's claims re-measured on the older slice (pools it never saw).
(1) user transactions per block at each d before T; (2) the keys the finder named (its discovery top 12 and held-out top 12 by d1-4 excess,
plus 'ANY event in another line pool'), each with pools at d = 0..12, d1-4 / d5-8 / d9-12 windows, the excess, the background rate per block in
L+4..T-13; (3) a fresh search on this slice (older two thirds = discovery, newer third = held out), the same excess statistic, to see whether
ANY key replicates within one slice; (4) the bot buy's signing time (its deadline argument - 1200 s) against T's block time.
Key definitions copied verbatim from the precursor angle's s6_precursors.py. Main set: the 3.0 line's current regime (launches from 04:22:19
UTC Oct 11, T at L+18..+55); the older regime (T at L+8..+10, 398 pools) only in (4)."""
import pickle, collections, statistics as st
from lib import *
E = pickle.load(open("events.pkl", "rb")); rows = E["rows"]; facts = {f["pid"]: f for f in E["facts"]}
D = pickle.load(open("parsed.pkl", "rb")); PP = {p["pid"]: p for p in D["pools"]}
kb = KV("blk"); SYS = "0x00000000000000000000000000000000000a4b05"
NEW = sorted([f["pid"] for f in E["facts"] if f["regime"] == "new" and f["near_ok"]], key=lambda k: facts[k]["L"])
n = len(NEW); A = set(NEW[: (2 * n) // 3]); B = set(NEW[(2 * n) // 3:]); S = set(NEW)
print(f"current-regime 3.0 pools with blocks [T-12, T+3]: {n}; L {facts[NEW[0]]['L']}..{facts[NEW[-1]]['L']} ({utc(D['t0'] + (facts[NEW[0]]['L'] - D['start']) / D['bps'])} -> "
      f"{utc(D['t0'] + (facts[NEW[-1]]['L'] - D['start']) / D['bps'])} UTC); T min {min(facts[k]['T'] for k in NEW)}")
print("\n(1) user txs per block at d blocks before T (T's block counted whole), current-regime pools:")
for d in range(0, 13):
    v = [sum(1 for t in kb.d[str(facts[k]["Tbn"] - d)]["txs"] if (t["from"] or "").lower() != SYS) for k in NEW]
    print(f"  d {d:2d}: mean {st.mean(v):.2f}  p50 {pct(v,.5)}")

def keys(r):   # verbatim from research/session_oct11/lines/analysis/T3/precursor/s6_precursors.py
    ks = [f"to+sel {r['tc'] if r['tc'] not in ('other','botwallet','linetoken','otherlauncher','puller') else r['to'][:10]}:{r['sel']}",
          f"cls {r['fc']}->{r['tc']}:{r['sel']}", f"from {r['fc'] if r['fc'] not in ('other',) else r['frm'][:10]}"]
    ks += [f"touch {t}" for t in r["touch"]]
    if r["val"] > 0 and r["sel"] == "": ks.append(f"eth-send {r['fc']}->{r['tc']}")
    if r["to"] == BOT: ks.append("ANY tx to the bot router")
    if r["fc"] in ("botwallet", "BUYER"): ks.append("ANY tx from a bot wallet")
    if r["tc"] == "POSM" and r["clen"] == 1444: ks.append("a 1444-byte PositionManager launch (any line)")
    if r["tc"] == "POSM": ks.append("ANY tx to the PositionManager")
    if r["fc"] == "BUYER": ks.append("ANY tx from T's buyer wallet")
    if r["fc"] == "LAUNCHER": ks.append("ANY tx from the pool's launcher")
    if r["fc"] in ("LAUNCHER", "otherlauncher"): ks.append("ANY tx from a line launcher (any pool)")
    if r["fc"] == "SENTINEL": ks.append("ANY tx from the sentinel 0xe71a69f4")
    if r["tc"] == "PERMIT2": ks.append("ANY tx to Permit2")
    if r["tc"] == "TOKEN" or any(t.startswith(("token", "pid", "pool_log")) for t in r["touch"]): ks.append("ANY tx touching the pool or its token")
    if any(t.startswith("buyer") for t in r["touch"]): ks.append("ANY tx touching T's buyer wallet")
    if r["val"] > 0 and r["tc"] in ("BUYER", "botwallet"): ks.append("ETH sent to a bot wallet")
    if any(t.startswith("otherline") for t in r["touch"]): ks.append("ANY event in another line pool")
    return ks
occ = collections.defaultdict(lambda: collections.defaultdict(set))   # key -> d -> pools
bgb = collections.defaultdict(lambda: collections.defaultdict(set))   # key -> pid -> blocks (L+4..T-13) holding it
for r in rows:
    if r["pos"] != "before" or r["pid"] not in S: continue
    for k in keys(r):
        if 0 <= r["d"] <= 12: occ[k][r["d"]].add(r["pid"])
        elif r["d"] > 12 and r["off"] >= 4: bgb[k][r["pid"]].add(r["bn"])
nbg = {k: max(0, facts[k]["Tbn"] - 13 - (facts[k]["L"] + 4) + 1) for k in NEW}
def w(k, a, b, X): return len(set().union(*[occ[k][d] & X for d in range(a, b + 1)]))
def exc(k, X): return (w(k, 1, 4, X) - (w(k, 5, 8, X) + w(k, 9, 12, X)) / 2) / len(X)
def bgrate(k, X):
    nb = sum(nbg[p] for p in X); return sum(len(bgb[k].get(p, ())) for p in X) / nb if nb else 0
def line(k, X):
    cnt = [len(occ[k][d] & X) for d in range(13)]
    return (f"  {k[:52]:52s} d1-4 {w(k,1,4,X):3d} d5-8 {w(k,5,8,X):3d} d9-12 {w(k,9,12,X):3d} excess {100*exc(k,X):+6.1f}%  bg/blk {100*bgrate(k,X):5.1f}% | "
            + " ".join(f"{x:2d}" for x in cnt))
NAMED_D = ["eth-send other->other", "cls other->other:", "cls other->other:a9059cbb", "from 0xc256a1bb", "from 0x769097a2", "from 0x4a6dbb33",
           "cls botwallet->UR:24856bc3", "to+sel 0xc8914bbb:ae7e8d81", "cls other->other:ae7e8d81", "to+sel 0x23070b6a:d1ffe0a2", "cls other->other:d1ffe0a2",
           "cls other->other:765e827f"]
NAMED_H = ["to+sel 0x00000000:fd9f1e10", "cls other->other:fd9f1e10", "cls other->other:095ea7b3", "to+sel 0xccc88a9d:0a2b8f36", "cls other->other:0a2b8f36",
           "from 0x99914a98", "to+sel 0x698f6005:3593564c", "cls other->other:4d819a2a", "cls other->other:7169b574", "to+sel 0xb740ddd4:00000000",
           "from 0xfb3d6d79", "cls other->other:00000000"]
FINDER = {"eth-send other->other": (12.8, 0.0), "cls other->other:": (10.5, -8.2), "cls other->other:a9059cbb": (9.8, -6.7), "from 0xc256a1bb": (4.5, 0.0),
          "from 0x769097a2": (4.5, 0.0), "from 0x4a6dbb33": (4.1, 6.0), "cls botwallet->UR:24856bc3": (3.8, -4.5), "to+sel 0xc8914bbb:ae7e8d81": (3.8, -3.0),
          "cls other->other:ae7e8d81": (3.8, -3.0), "to+sel 0x23070b6a:d1ffe0a2": (3.8, -0.7), "cls other->other:d1ffe0a2": (3.8, -0.7), "cls other->other:765e827f": (3.4, -0.7),
          "to+sel 0x00000000:fd9f1e10": (3.0, 17.9), "cls other->other:fd9f1e10": (3.0, 17.9), "cls other->other:095ea7b3": (-4.5, 15.7), "to+sel 0xccc88a9d:0a2b8f36": (-4.1, 12.7),
          "cls other->other:0a2b8f36": (-4.1, 12.7), "from 0x99914a98": (-3.0, 11.9), "to+sel 0x698f6005:3593564c": (0.8, 11.9), "cls other->other:4d819a2a": (2.3, 10.4),
          "cls other->other:7169b574": (3.0, 10.4), "to+sel 0xb740ddd4:00000000": (-1.1, 9.7), "from 0xfb3d6d79": (-1.1, 9.7), "cls other->other:00000000": (-4.9, 7.5)}
print(f"\n(2) the finder's named keys on THIS slice (n {n}); columns: pools with the key in d1-4 / d5-8 / d9-12, excess of d1-4 over the mean of the"
      f" other two (share of pools), background share of blocks L+4..T-13 holding it | pools at d = 0..12;  finder's (discovery, held-out) excess")
for title, ks in (("finder's discovery top 12", NAMED_D), ("finder's held-out top 12", NAMED_H),
                  ("named structural keys", ["ANY event in another line pool", "touch otherline_3.0:Swap", "ANY tx to the bot router", "ANY tx from a bot wallet",
                                             "ANY tx to the PositionManager", "a 1444-byte PositionManager launch (any line)", "ANY tx touching the pool or its token",
                                             "ANY tx touching T's buyer wallet", "ETH sent to a bot wallet", "ANY tx from a line launcher (any pool)", "ANY tx to Permit2",
                                             "ANY tx from the sentinel 0xe71a69f4"])):
    print(f" -- {title}")
    for k in ks:
        f = FINDER.get(k); print(line(k, S) + (f"   finder {f[0]:+.1f}/{f[1]:+.1f}" if f else ""))
print("\n(3) a fresh search inside this slice: top 15 keys by d1-4 excess on its older two thirds (n %d), the same keys on its newest third (n %d)" % (len(A), len(B)))
allk = [k for k in occ if w(k, 1, 4, S) >= 3]
for X, Y, la, lb in ((A, B, "older 2/3", "newest 1/3"), (B, A, "newest 1/3", "older 2/3")):
    top = sorted(allk, key=lambda k: -exc(k, X))[:15]
    print(f" -- top on the {la}, then on the {lb}")
    for k in top: print(f"  {k[:60]:60s} {la} {100*exc(k, X):+6.1f}%   {lb} {100*exc(k, Y):+6.1f}%   whole slice {100*exc(k, S):+6.1f}%")
# how big is the noise? the excess of every key with >= 5 pools in d1-12 under a random relabelling of d (block-shuffle null): the d windows of
# each pool rotated by a random shift, the max excess over keys
import random
random.seed(1)
cand = [k for k in occ if sum(len(occ[k][d] & S) for d in range(1, 13)) >= 5]
obs = sorted((exc(k, S), k) for k in cand)[-1]
mx = []
for it in range(200):
    perm = {p: random.sample(range(1, 13), 12) for p in S}   # per pool, a random relabelling of d 1..12
    def wp(k, a, b): return len({p for p in S for d in range(1, 13) if perm[p][d - 1] in range(a, b + 1) and p in occ[k][d]})
    mx.append(max((wp(k, 1, 4) - (wp(k, 5, 8) + wp(k, 9, 12)) / 2) / len(S) for k in cand))
print(f"\nnull check: {len(cand)} keys with >= 5 pool-hits in d1-12; the largest observed d1-4 excess on the whole slice {100*obs[0]:+.1f}% ({obs[1]});"
      f" the largest excess when each pool's d labels 1..12 are randomly permuted (200 draws): p50 {100*pct(mx,.5):+.1f}% p95 {100*pct(mx,.95):+.1f}% max {100*max(mx):+.1f}%")
# (4) the bot buy's own signing time: its calldata deadline - 1200 s vs the T block's timestamp
print("\n(4) the bot's first buy: deadline words in its calldata vs T's block time")
for reg in ("new", "old"):
    G = [p for p in D["pools"] if p["regime"] == reg and p["T"] is not None and p["Tinput"]]
    diffs = collections.Counter(); lagL = collections.Counter(); nn = 0
    for p in G:
        inp = p["Tinput"]; ws = [int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16) for i in range((len(inp) - 10) // 64)]
        tsT = kb.d[str(p["Tbn"])]["ts"]; tsL = kb.d.get(str(p["L"] + 1), {}).get("ts")
        cands = [x for x in ws if abs(x - tsT) < 4000]
        if not cands: continue
        nn += 1; dl = cands[0]; diffs[dl - tsT] += 1
        if tsL: lagL[(dl - 1200) - (tsL)] += 1
    print(f"  {reg}: n {nn} of {len(G)}; deadline - ts(T block) seconds: {sorted(diffs.items())}; (deadline - 1200) - ts(L+1) seconds: p10/50/90 "
          f"{pct(list(lagL.elements()),.1)}/{pct(list(lagL.elements()),.5)}/{pct(list(lagL.elements()),.9)}")
