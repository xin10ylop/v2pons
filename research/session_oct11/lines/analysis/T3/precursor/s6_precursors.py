"""Stage 6: the precursor search. For every transaction type (several granularities: exact target+selector, sender class+target class+selector,
exact sender, what it touches), in how many pools does it occur d blocks before T (d = 0 means T's own block, ahead of the bot's tx), for
d = 0..12, against its background rate (d = 5..12 and the blocks L+4..T-13). A usable precursor would sit in most pools at one d in 1..4 and
rarely elsewhere. Discovery on the older two thirds of the pools, the measurement on the most recent third (held out).
Needs events.pkl (s4_classify.py)."""
import pickle, collections, sys
from lib import *
E = pickle.load(open("events.pkl", "rb")); rows = E["rows"]; facts = {f["pid"]: f for f in E["facts"]}
full = [f for f in E["facts"] if f["have_blocks"] == f["need_blocks"]]
near_ok = {f["pid"] for f in E["facts"] if f.get("near_ok")}
pids = sorted(near_ok, key=lambda k: facts[k]["L"])
n = len(pids); disc = set(pids[: (2 * n) // 3]); hold = set(pids[(2 * n) // 3:])
print(f"pools with the whole window T-12..T: {n} (discovery {len(disc)}, held out {len(hold)}; held-out L from {min(facts[k]['L'] for k in hold) if hold else None})")
def keys(r):
    ks = [f"to+sel {r['tc'] if r['tc'] not in ('other','botwallet','linetoken','otherlauncher','puller') else r['to'][:10]}:{r['sel']}",
          f"cls {r['fc']}->{r['tc']}:{r['sel']}", f"from {r['fc'] if r['fc'] not in ('other',) else r['frm'][:10]}"]
    ks += [f"touch {t}" for t in r["touch"]]
    if r["val"] > 0 and r["sel"] == "": ks.append(f"eth-send {r['fc']}->{r['tc']}")
    return ks
occ = collections.defaultdict(lambda: collections.defaultdict(set))   # key -> d -> set(pid)
bg = collections.defaultdict(lambda: collections.defaultdict(int))     # key -> pid -> count of blocks with it in L+4..T-13
bgblocks = collections.Counter()
for r in rows:
    if r["pos"] != "before" or r["pid"] not in near_ok: continue
    for k in keys(r):
        if 0 <= r["d"] <= 12: occ[k][r["d"]].add(r["pid"])
seenblk = collections.defaultdict(set)
for r in rows:
    if r["pos"] != "before" or r["pid"] not in near_ok: continue
    if r["d"] > 12 and r["off"] >= 4:
        for k in keys(r): seenblk[(k, r["pid"])].add(r["off"])
for f in E["facts"]:
    if f["pid"] in near_ok and f["have_blocks"] == f["need_blocks"]: bgblocks[f["pid"]] = max(0, f["Tbn"] - 13 - (f["L"] + 4) + 1)
def rate(k, S):
    """background: share of blocks (L+4..T-13, pools with the whole range) holding the key"""
    nb = sum(bgblocks[p] for p in S if p in bgblocks); hit = sum(len(seenblk.get((k, p), ())) for p in S if p in bgblocks)
    return hit / nb if nb else None
def table(S, label, top=40):
    print(f"\n== {label}: n {len(S)} pools. Per key: pools with it at d = 0,1,2,...,12 blocks before T (d=0: T's block, ahead of the bot's tx); "
          f"'win1-4' = pools with it anywhere in d 1..4; 'bg/blk' = share of blocks L+4..T-13 holding it; 'exp1-4' = pools expected in a 4-block window at that rate")
    cand = []
    for k, dd in occ.items():
        cnt = [len(dd[d] & S) for d in range(13)]
        w14 = len(set().union(*[dd[d] & S for d in range(1, 5)]))
        r = rate(k, S); exp = len(S) * (1 - (1 - r) ** 4) if r is not None else None
        if w14 >= 0.15 * len(S): cand.append((w14, k, cnt, r, exp))
    cand.sort(key=lambda x: -x[0])
    for w14, k, cnt, r, exp in cand[:top]:
        print(f"  {k[:62]:62s} win1-4 {w14:3d} ({100*w14/len(S):3.0f}%) exp {exp if exp is None else round(exp,1)!s:>6} bg/blk {('%.3f' % r) if r is not None else '  -  '} | " + " ".join(f"{c:3d}" for c in cnt))
    return cand
c1 = table(disc, "DISCOVERY (older two thirds)")
c2 = table(hold, "HELD OUT (most recent third)")
