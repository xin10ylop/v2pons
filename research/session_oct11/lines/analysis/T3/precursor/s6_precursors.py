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
        base = sum(cnt[5:13]) / 8; peak = max(cnt[1:5]); dpk = 1 + cnt[1:5].index(peak)
        w58 = len(set().union(*[dd[d] & S for d in range(5, 9)])); w912 = len(set().union(*[dd[d] & S for d in range(9, 13)]))
        cand.append(dict(k=k, cnt=cnt, w14=w14, w58=w58, w912=w912, r=r, exp=exp, base=base, peak=peak, dpk=dpk, ratio=(peak + 0.5) / (base + 0.5)))
    def show(c):
        print(f"  {c['k'][:60]:60s} win1-4 {c['w14']:3d} ({100*c['w14']/len(S):3.0f}%) exp {c['exp'] if c['exp'] is None else round(c['exp'],1)!s:>6} "
              f"peak d={c['dpk']} {c['peak']:3d} vs bg {c['base']:5.1f} (x{c['ratio']:.1f}) | " + " ".join(f"{x:3d}" for x in c["cnt"]))
    print("  -- by coverage of d 1..4 (top %d)" % top)
    for c in sorted(cand, key=lambda c: -c["w14"])[:top]: show(c)
    print("  -- by the peak at one d in 1..4 against d 5..12 (keys seen in >= 10% of pools at their peak)")
    for c in sorted([c for c in cand if c["peak"] >= 0.10 * len(S)], key=lambda c: -c["ratio"])[:25]: show(c)
    print("  -- same-width windows: pools with the key in d 1..4 vs d 5..8 vs d 9..12, by the excess of 1..4 over the mean of the other two (top 15)")
    for c in sorted(cand, key=lambda c: -(c["w14"] - (c["w58"] + c["w912"]) / 2))[:15]:
        print(f"  {c['k'][:60]:60s} d1-4 {c['w14']:3d}  d5-8 {c['w58']:3d}  d9-12 {c['w912']:3d}  excess {c['w14'] - (c['w58'] + c['w912']) / 2:+5.1f} ({100 * (c['w14'] - (c['w58'] + c['w912']) / 2) / len(S):+.0f}% of pools)")
    print("  -- named keys")
    for c in sorted([c for c in cand if c["k"].startswith(("ANY", "a 1444", "ETH sent"))], key=lambda c: c["k"]): show(c)
    return cand
c1 = table(disc, "DISCOVERY (older two thirds)")
c2 = table(hold, "HELD OUT (most recent third)")
