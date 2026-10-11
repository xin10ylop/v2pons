"""Stage 5: is there ANY transaction type at a stable 1-4 block lead to T on the test slice (beyond the candidate's pool/token/buyer touches)?
Every tx in the whole blocks [L+4, T] of each test pool, keyed several ways (exact to+selector, sender, sender class->target class:selector,
plus line-level keys: a bot buy c1120e3d in ANY pool, any tx from a bot wallet, any tx to the bot router, a 1,444-byte PositionManager launch,
a pull a0f7978d, a Swap/ML log in another line pool, a plain ETH send, a failed tx). Per key: pools holding it at d = T-block - block
(d = 0: T's block ahead of the bot tx) for d = 0..12, and the per-block background over [L+4, T-13]. As a trigger: fire on every occurrence
of the key in [L+4, T) of the pool and call 'hit' when T comes 1-4 blocks after it; precision = hits / fires, recall = pools with a hit."""
import pickle, collections, os
from lib import *
os.chdir(HERE)
D = pickle.load(open("u2_parsed.pkl", "rb")); kb = KV("blk"); kr = KV("rcp")
SYS = "0x00000000000000000000000000000000000a4b05"
ALLP = D["pools"]
BOTW = {s["eoa"] for p in ALLP for s in p["sw"] if s["who"] == "bot"}
LINE_PID = {p["pid"] for p in ALLP}
G = [p for p in ALLP if p["recent2h"] and p["T"] is not None and not p["finder"]]
def cls(a):
    if a == BOT: return "BOTROUTER"
    if a == UR: return "UR"
    if a == POSM: return "POSM"
    if a == PM: return "PM"
    if a == PERMIT2: return "PERMIT2"
    if a == SENTINEL: return "SENTINEL"
    if a in BOTW: return "botwallet"
    return "other"
def keys(t, rc, p):
    inp = (t.get("input") or "0x").lower(); frm = t["from"].lower(); to = (t.get("to") or "").lower(); sel = inp[2:10]
    ks = {f"to+sel {to[:10]}:{sel}", f"from {frm[:10]}", f"cls {cls(frm)}->{cls(to)}:{sel}"}
    if to == BOT and sel == "c1120e3d": ks.add("LINE a bot buy c1120e3d (any pool)")
    if to == BOT: ks.add("LINE any tx to the bot router")
    if to == BOT and sel == "a0f7978d": ks.add("LINE a pull a0f7978d (any pool)")
    if frm in BOTW: ks.add("LINE any tx from a bot wallet")
    if to == POSM and (len(inp) - 2) // 2 == 1444: ks.add("LINE a 1444-byte PositionManager launch (any line)")
    if int(t["value"], 16) > 0 and sel == "": ks.add("LINE plain ETH send")
    if (rc or {}).get("status") == "0x0": ks.add("LINE failed tx")
    for l in (rc or {}).get("logs", []):
        if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() in LINE_PID and l["t"][1].lower() != p["pid"]:
            ks.add("LINE event in another 3.0 pool:" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "x"))
        if l["a"] == PM and l["t"][0] == T_INIT: ks.add("LINE any v4 Initialize")
    return ks
cov = collections.defaultdict(lambda: collections.defaultdict(set)); bg = collections.Counter(); bgn = 0
fires = collections.defaultdict(list)        # key -> list of (pid, d) for every block holding it in [L+4, T)
for p in G:
    for bn in range(p["L"] + 4, p["Tbn"] + 1):
        b = kb.d[str(bn)]; rc = {x["tx"]: x for x in kr.d[str(bn)]}; d = p["Tbn"] - bn; ks = set()
        for t in b["txs"]:
            if t.get("type") == "0x6a" or (t.get("from") or "").lower() == SYS: continue
            if bn == p["Tbn"] and int(t["transactionIndex"], 16) >= p["Tti"]: continue
            ks |= keys(t, rc.get(t["hash"]), p)
        for k in ks:
            if d <= 12: cov[k][d].add(p["pid"])
            if d >= 1: fires[k].append((p["pid"], d))
        if d >= 13: bgn += 1; bg.update(ks)
n = len(G)
print(f"test slice {n} pools; background blocks [L+4, T-13]: {bgn}")
rows = []
for k, byd in cov.items():
    c = [len(byd.get(d, ())) for d in range(13)]
    win = len(set().union(*[byd.get(d, set()) for d in range(1, 5)]))
    peak_d = max(range(1, 5), key=lambda d: c[d]); rate = bg[k] / bgn if bgn else 0
    f = fires[k]; hits = sum(1 for _, d in f if 1 <= d <= 4); rec = len({pid for pid, d in f if 1 <= d <= 4})
    rows.append((k, c, win, peak_d, rate, len(f), hits, rec))
print("\n-- top 25 keys by the most pools at ONE d in 1..4 (a stable lead would put most pools at one d); counts at d = 0..12; bg = share of background blocks holding it")
for k, c, win, pd, rate, nf, hits, rec in sorted(rows, key=lambda r: -r[1][r[3]])[:25]:
    print(f"  {k[:62]:62s} peak d={pd} {c[pd]:2d}/{n} ({100*c[pd]/n:3.0f}%) bg/blk {rate:.2f} | {' '.join('%2d' % x for x in c)} | as trigger: fires {nf:4d} hits {hits:3d} prec {hits/max(1,nf):.2f} recall {rec}/{n}")
print("\n-- line-level keys")
for k, c, win, pd, rate, nf, hits, rec in sorted([r for r in rows if r[0].startswith("LINE")], key=lambda r: -r[2]):
    print(f"  {k[:62]:62s} in d1-4 {win:2d}/{n} peak d={pd} {c[pd]:2d} bg/blk {rate:.2f} | {' '.join('%2d' % x for x in c)} | trigger: fires {nf:4d} hits {hits:3d} prec {hits/max(1,nf):.2f} recall {rec}/{n}")
best = max(rows, key=lambda r: r[1][r[3]])
print(f"\nbest single-d coverage of any key: {best[0]} at d={best[3]}: {best[1][best[3]]}/{n}; a +-1-block predictor needs most pools at one d with a low background")
# keys reaching >= 50% at one d in 1..4
strong = [r for r in rows if max(r[1][1:5]) >= n / 2]
print("keys in >= half the pools at a single d in 1..4:", [(r[0], r[1][1:5], round(r[4], 2)) for r in strong])
for r in strong:
    print(f"   {r[0]}: background share of blocks {r[4]:.2f} -> expected per block {r[4]*n:.1f} pools vs observed {r[1][1:5]} (i.e. no excess = ubiquitous)")
