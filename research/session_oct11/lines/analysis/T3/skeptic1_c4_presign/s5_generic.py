"""Stage 5: any tx type at a stable 1-4 block lead to T, on my slice, with a hold-out (discovery = older two thirds, test = newest third).
Keys per tx in blocks T-12..T (d = T - block; d 0 = T's block ahead of the bot's tx): to+selector, sender (if seen in >= 4 pools), and classes
(to the bot router, from a bot wallet, a 3.0 launch, any PositionManager call, Permit2, Universal Router, plain ETH send, the sentinel,
a bot buy in another pool, a bot-wallet sell). Per key: pools with it anywhere in d 1..4 vs the expectation from its per-block rate in d 5..12;
the peak d. A usable rule must fire in d 1..4 (or at one fixed d) in nearly every pool and rarely elsewhere.  usage: s5_generic.py <slice>"""
import sys, pickle, collections
from lib import *
name = sys.argv[1]; kb = KV("blk")
D = pickle.load(open(f"parsed_{name}.pkl", "rb")); botw = D["botw"]
P = sorted([p for p in D["pools"] if p["T"] is not None and all(str(n) in kb.d for n in range(p["Tbn"] - 12, p["Tbn"] + 1))], key=lambda p: p["L"])
n = len(P); disc, hold = P[: (2 * n) // 3], P[(2 * n) // 3:]
def keys(t, p):
    fr = (t["from"] or "").lower(); to = (t.get("to") or "").lower(); inp = (t["input"] or "0x").lower(); sel = inp[2:10]
    k = {"to+sel " + to[:10] + ":" + sel, "from " + fr[:10]}
    if to == BOT: k.add("CLS to bot router (any)"); k.add("CLS to bot router:" + sel)
    if fr in botw: k.add("CLS from a bot wallet (any)")
    if fr in botw and to == UR: k.add("CLS bot-wallet sell via UR")
    if to == BOT and sel == "c1120e3d": k.add("CLS bot buy in another pool")
    if to == POSM: k.add("CLS PositionManager call")
    if to == POSM and int(t["value"], 16) == 3 * 10 ** 18 and (len(inp) - 2) // 2 == 1444: k.add("CLS a 3.0 launch")
    if to == POSM and (len(inp) - 2) // 2 == 1444: k.add("CLS a 1444-byte launch (any line)")
    if to == PERMIT2: k.add("CLS Permit2")
    if to == UR: k.add("CLS Universal Router")
    if inp == "0x": k.add("CLS plain ETH send")
    if fr.startswith(SENTINEL_PREFIX): k.add("CLS sentinel")
    if fr == p["launcher"]: k.add("CLS this pool's launcher")
    return k
def table(S):
    pres = collections.defaultdict(lambda: collections.defaultdict(set))   # key -> d -> pools
    for i, p in enumerate(S):
        T = p["Tbn"]
        for d in range(0, 13):
            for t in kb.d[str(T - d)]["txs"]:
                if d == 0 and int(t["transactionIndex"], 16) >= p["Tti"]: continue
                if (t["from"] or "").lower() == p["buyer"] and d == 0: continue
                for k in keys(t, p): pres[k][d].add(i)
    return pres
def stats(pres, k, N):
    per_d = [len(pres[k][d]) for d in range(13)]
    win = len(set().union(*[pres[k][d] for d in (1, 2, 3, 4)]))
    r = sum(per_d[5:13]) / (8 * N)                           # per (pool, block) rate in d 5..12
    exp = N * (1 - (1 - r) ** 4)
    peak = max(range(1, 5), key=lambda d: per_d[d])
    return dict(per_d=per_d, win=win, exp=exp, excess=win - exp, peak=peak, peak_n=per_d[peak], bg=sum(per_d[5:13]) / 8)
Pd, Ph = table(disc), table(hold)
fromcount = collections.Counter()
for k in Pd:
    if k.startswith("from "): fromcount[k] = len(set().union(*Pd[k].values()))
cand = [k for k in Pd if not k.startswith("from ") or fromcount[k] >= 4]
print(f"slice {name}: pools {n}; discovery {len(disc)} (L {disc[0]['L']}..{disc[-1]['L']}), held out {len(hold)} (L {hold[0]['L']}..{hold[-1]['L']})")
print("user txs per block by d (all pools):", [round(sum(len(kb.d[str(p['Tbn'] - d)]['txs']) for p in P) / n, 2) for d in range(13)])
rows = sorted(((stats(Pd, k, len(disc)), k) for k in cand), key=lambda x: -x[0]["excess"])
print("\nDISCOVERY: top 20 keys by excess of pools with the key in d 1..4 over the d 5..12 rate  | pools at d = 0..12")
for s, k in rows[:20]:
    print(f"  {k[:52]:52s} win1-4 {s['win']:3d}/{len(disc)} ({100*s['win']/len(disc):3.0f}%) exp {s['exp']:5.1f} excess {s['excess']:+5.1f} | {s['per_d']}")
rows2 = sorted(((stats(Pd, k, len(disc)), k) for k in cand if stats(Pd, k, len(disc))["bg"] > 0 or True), key=lambda x: -(x[0]["peak_n"] - x[0]["bg"]))
print("\nDISCOVERY: top 10 keys by the peak at one d in 1..4 over the mean of d 5..12")
for s, k in rows2[:10]:
    print(f"  {k[:52]:52s} peak d={s['peak']} {s['peak_n']:3d} vs bg {s['bg']:5.2f} | {s['per_d']}")
print("\nCLASSES on discovery (pools at d = 0..12):")
for k in sorted(k for k in cand if k.startswith("CLS")):
    s = stats(Pd, k, len(disc)); print(f"  {k[:52]:52s} win1-4 {s['win']:3d} exp {s['exp']:5.1f} | {s['per_d']}")
test = [k for _, k in rows[:10]] + [k for _, k in rows2[:5] if k not in [k2 for _, k2 in rows[:10]]]
print(f"\nHELD OUT ({len(hold)} pools): the discovery's top keys")
for k in test:
    s = stats(Ph, k, len(hold)) if k in Ph else dict(win=0, exp=0, excess=0, per_d=[0] * 13)
    print(f"  {k[:52]:52s} win1-4 {s['win']:3d}/{len(hold)} ({100*s['win']/len(hold):3.0f}%) exp {s['exp']:5.1f} excess {s['excess']:+5.1f} | {s['per_d']}")
best = max(test, key=lambda k: (stats(Ph, k, len(hold))["win"] if k in Ph else 0))
print(f"\nbest held-out coverage: {best}")
