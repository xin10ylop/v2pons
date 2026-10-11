"""Stage 5: details behind k4. (a) what the 7422a284 txs to the bot router are; (b) the lead d = T - b of the rule's FIRST fire after arming at
L+a (what the engine would act on), for several a, and the share landing in the survivable window under the measured pre-T lags; (c) a
blind control: the same rule fired at a random block with the same per-block rate (5.8%), to show the precursor adds nothing; (d) the
break-even in-time share."""
import pickle, sys, os, collections, random, statistics as st
from lib import *
os.chdir(HERE)
D = pickle.load(open("k2_parsed.pkl", "rb")); R = pickle.load(open("k4_rule.pkl", "rb")); kb = KV("blk")
P = [p for p in D["pools"] if p["pid"] in set(R["P"])]; pre = R["pre"]["V0 any tx to the bot router, other pool"]
# (a)
c = collections.Counter(); ex = None
for p in P:
    for bn in range(p["L"] + 1, p["Tbn"] + 1):
        for t in kb.d[str(bn)]["txs"]:
            if (t.get("to") or "").lower() == BOT and (t.get("input") or "")[2:10] == "7422a284":
                c[(t["from"][:10], int(t["value"], 16) / 1e18, (len(t["input"]) - 2) // 2)] += 1; ex = ex or t
print("7422a284 to the bot router (from, value ETH, bytes):", c.most_common(6))
if ex: print("  words:", [ex["input"][10 + 64 * i: 10 + 64 * (i + 1)].lstrip("0")[:40] for i in range(min(8, (len(ex["input"]) - 10) // 64))])
# (b)
print("\nthe rule's first fire after arming at L+a: lead d = T - b (b = the precursor's block), and where the buy lands (k = 1: b+1, k = 2: b+2)")
for a in (4, 10, 20, 30, 40):
    d = []
    for p in P:
        f = [bn for bn, _ in pre[p["pid"]] if bn >= p["L"] + a]
        d.append(p["Tbn"] - f[0] if f else None)
    dd = [x for x in d if x is not None]
    w = {k: {lag: sum(1 for x in dd if 0 <= x - k <= lag - 2) for lag in (3, 4)} for k in (1, 2)}
    print(f"  a {a:2d}: fires {len(dd)}/{len(P)}; lead p10/25/50/75/90 {[pct(dd, q) for q in (.1, .25, .5, .75, .9)]}; lead <= 0 (late) {sum(1 for x in dd if x <= 0)}; "
          f"survivable (lands in [T+2-lag, T]): k1 lag3 {w[1][3]}, k1 lag4 {w[1][4]}, k2 lag3 {w[2][3]}, k2 lag4 {w[2][4]}; lead > 4 (pulled) {sum(1 for x in dd if x > 4)}")
# (c) blind control
random.seed(7)
rate = 0.058
print(f"\nblind control: a fire at each block with probability {rate} (no information), armed at L+a; 2000 draws per pool; share of pools whose first fire has lead d in 1..4")
for a in (4, 20, 30, 40):
    real = []; blind = []
    for p in P:
        f = [bn for bn, _ in pre[p["pid"]] if bn >= p["L"] + a]
        if f: real.append(1 <= p["Tbn"] - f[0] <= 4)
        hits = n = 0
        for _ in range(2000):
            b = p["L"] + a
            while b <= p["Tbn"] and random.random() > rate: b += 1
            if b <= p["Tbn"]: n += 1; hits += 1 <= p["Tbn"] - b <= 4
        if n: blind.append(hits / n)
    print(f"  a {a:2d}: rule {sum(real)}/{len(real)} = {100 * sum(real) / max(1, len(real)):.0f}% of its fires in d 1..4; blind {100 * st.mean(blind):.0f}%")
g = [x for x in R["gain"].values() if x is not None]; loss = 1.0 + 0.02 / 5
print(f"\nbreak-even: in-time gain {100 * st.mean(g):.2f}% vs -{100 * loss:.1f}% when pulled: needs in-time / (in-time + pulled) >= {100 * loss / (loss + st.mean(g)):.1f}%")
