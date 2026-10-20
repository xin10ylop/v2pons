"""Stage 5: re-measure the finder's precursor keys on the new slice (48 pools launched in the most recent 2 hours, all after the finder's
head). keys() is copied verbatim from ../precursor/s6_precursors.py. For each key: pools with it at d = 0..12 blocks before T (d = 0: T's
block, ahead of the bot's tx), pools with it anywhere in d 1-4 / 5-8 / 9-12, the excess of 1-4 over the mean of the other two (the
finder's statistic), and for keys visible in the transaction list alone the per-block background in L+4..T-13.
Then the slice's own top keys, measured back on the finder's final events.pkl (discovery = older 2/3, held out = newest 1/3)."""
import pickle, collections, statistics as st, os
from lib import *
os.chdir(HERE)
E = pickle.load(open("s4_rows.pkl", "rb")); rows = E["rows"]; facts = {f["pid"]: f for f in E["facts"]}
S = set(f["pid"] for f in E["facts"] if f["near_ok"]); n = len(S)
def keys(r):
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
def xkeys(r):     # extra keys of this skeptic (transaction list only, so their background is measurable everywhere)
    ks = []
    if r["bot_buy"]: ks.append("X bot buy tx (bot router c1120e3d), another pool")
    if r["bot_any"]: ks.append("X any bot-router tx, another pool")
    if r["other_pool_logs"]: ks.append("X any PoolManager log in another pool")
    return ks
RCP_KEYS = lambda k: False   # receipts cover every block [L-3, T+3] (s3b)
def build(rows, S, kf):
    occ = collections.defaultdict(lambda: collections.defaultdict(set)); seen = collections.defaultdict(set)
    for r in rows:
        if r["pos"] != "before" or r["pid"] not in S: continue
        for k in kf(r):
            if 0 <= r["d"] <= 12: occ[k][r["d"]].add(r["pid"])
            if r["d"] > 12 and r["off"] >= 4: seen[(k, r["pid"])].add(r["off"])
    return occ, seen
kf = lambda r: keys(r) + xkeys(r)
occ, seen = build(rows, S, kf)
bgblocks = {p: max(0, facts[p]["Tbn"] - 13 - (facts[p]["L"] + 4) + 1) for p in S}
def stats(occ, k, S):
    w = lambda a, b: len(set().union(*[occ[k][d] & S for d in range(a, b + 1)]))
    cnt = [len(occ[k][d] & S) for d in range(13)]
    return cnt, w(1, 4), w(5, 8), w(9, 12), (w(1, 4) - (w(5, 8) + w(9, 12)) / 2) / len(S)
def bg(k):
    if RCP_KEYS(k): return None
    nb = sum(bgblocks.values()); hit = sum(len(seen.get((k, p), ())) for p in S); return hit / nb
SYS = "0x00000000000000000000000000000000000a4b05"
print(f"slice: {n} pools (L {min(facts[p]['L'] for p in S)}..{max(facts[p]['L'] for p in S)}), every block [L-3, T+3] with its txs, receipts for [T-12, T+3]")
print("\n(A) user txs per block at d blocks before T (T's block counted whole):")
kb = KV("blk")
for d in range(0, 13):
    v = [sum(1 for t in kb.d[str(facts[k]["Tbn"] - d)]["txs"] if (t["from"] or "").lower() != SYS) for k in S]
    print(f"  d {d:2d}: mean {st.mean(v):.2f}")
FIND_DISC = ["eth-send other->other", "cls other->other:", "cls other->other:a9059cbb", "from 0xc256a1bb", "from 0x769097a2", "from 0x4a6dbb33",
             "cls botwallet->UR:24856bc3", "to+sel 0xc8914bbb:ae7e8d81", "cls other->other:ae7e8d81", "to+sel 0x23070b6a:d1ffe0a2", "cls other->other:d1ffe0a2",
             "cls other->other:765e827f"]
FIND_HOLD = ["to+sel 0x00000000:fd9f1e10", "cls other->other:fd9f1e10", "cls other->other:095ea7b3", "to+sel 0xccc88a9d:0a2b8f36", "cls other->other:0a2b8f36",
             "from 0x99914a98", "to+sel 0x698f6005:3593564c", "cls other->other:4d819a2a", "cls other->other:7169b574", "to+sel 0xb740ddd4:00000000",
             "from 0xfb3d6d79", "cls other->other:00000000"]
EXTRA = ["ANY event in another line pool", "touch otherline_3.0:Swap", "touch otherline_2.433:Swap", "X bot buy tx (bot router c1120e3d), another pool",
         "X any bot-router tx, another pool", "X any PoolManager log in another pool", "ANY tx to the bot router", "ANY tx from a bot wallet",
         "ANY tx to the PositionManager", "a 1444-byte PositionManager launch (any line)", "ANY tx to Permit2", "ANY tx touching the pool or its token",
         "ANY tx touching T's buyer wallet", "ANY tx from T's buyer wallet", "ETH sent to a bot wallet", "ANY tx from the sentinel 0xe71a69f4"]
FE = pickle.load(open(os.path.join(HERE, "..", "precursor", "events.pkl"), "rb")); ff = {f["pid"]: f for f in FE["facts"]}
fp = sorted([f["pid"] for f in FE["facts"] if f["near_ok"]], key=lambda k: ff[k]["L"]); fn = len(fp)
FD, FH = set(fp[: (2 * fn) // 3]), set(fp[(2 * fn) // 3:])
focc, _ = build(FE["rows"], FD | FH, keys)
def line(k):
    cnt, a, b, c, e = stats(occ, k, S); r = bg(k)
    fe1 = stats(focc, k, FD)[4] if k in focc else 0.0; fe2 = stats(focc, k, FH)[4] if k in focc else 0.0
    exp = f"{100 * (1 - (1 - r) ** 4):4.0f}%" if r is not None else "   n/a"
    print(f"  {k[:58]:58s} slice d1-4 {a:2d} d5-8 {b:2d} d9-12 {c:2d} excess {100*e:+6.1f}% | bg/blk {'  n/a' if r is None else f'{100*r:4.1f}%'} exp1-4 {exp} | finder disc {100*fe1:+6.1f}% hold {100*fe2:+6.1f}% | d0..12 " + " ".join(f"{x:2d}" for x in cnt))
print(f"\n(B) the finder's discovery-top keys on the slice (n {n}); finder's own sets: discovery {len(FD)}, held out {len(FH)} (its final events.pkl)")
for k in FIND_DISC: line(k)
print("\n(C) the finder's held-out-top keys on the slice")
for k in FIND_HOLD: line(k)
print("\n(D) named keys, the other-line-pool keys (consistent in the finder's FINAL events.pkl, which its s6b replicate predates), and this skeptic's extra keys")
for k in EXTRA: line(k)
print("\n(E) the slice's own top 15 keys by the d1-4 excess, measured back on the finder's sets")
top = sorted(occ, key=lambda k: -stats(occ, k, S)[4])[:15]
for k in top: line(k)
nk = len(occ); print(f"\nkeys seen in d 0..12 on the slice: {nk}")
# null: the same search with T replaced by a fake anchor T' = T - s (s = 13..20; pools with T' - 12 >= L + 1): how large is the top
# excess when there is nothing to find?
print("\n(F) null: the top d1-4 excess over all keys with a fake anchor T' = T - s (same pools, same blocks, nothing to find)")
real = []
for sh in [0] + list(range(13, 21)):
    Sp = set(p for p in S if facts[p]["T"] - sh - 12 >= 1)
    oc = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if r["pid"] not in Sp: continue
        dd = r["d"] - sh
        if sh == 0 and r["pos"] != "before": continue
        if sh > 0 and not (r["pos"] == "before" and r["d"] > sh): continue
        if 1 <= dd <= 12:
            for k in kf(r): oc[k][dd].add(r["pid"])
    ex = sorted(((stats(oc, k, Sp)[4], k) for k in oc), reverse=True)
    print(f"  shift {sh:2d} pools {len(Sp)}: top excess {100*ex[0][0]:+5.1f}% ({ex[0][1][:40]}), 2nd {100*ex[1][0]:+5.1f}%, 5th {100*ex[4][0]:+5.1f}%, 15th {100*ex[14][0]:+5.1f}%"
          + (f"; fd9f1e10 {100*stats(oc, 'to+sel 0x00000000:fd9f1e10', Sp)[4]:+5.1f}%" if 'to+sel 0x00000000:fd9f1e10' in oc else ""))
pickle.dump({"occ": {k: dict(v) for k, v in occ.items()}, "S": S}, open("s5_occ.pkl", "wb"))
