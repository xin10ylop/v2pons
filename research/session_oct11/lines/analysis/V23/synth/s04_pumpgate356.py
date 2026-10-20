"""Synthesizer step 4: the 356-B d27d1e00 value-0 line (111 launches, rule K60 -> +260). The two reaction skeptics disagree on whether an
early outside buy goes with no pump (the 97c7ba1b lens: pumped 14% vs 48% in its 101 356-B pools; the 356 lens: no deterrence). Our own
buy at +60 is an early outside buy, so this decides the line. Recomputed here on the 111 launches with the 97c7ba1b reaction skeptic's buyer
classification (V23/reaction_V3_tok_tok_97c7ba1b.../rc.py, imported read-only): operator = launch wallets / pull senders of lc:89885b75,
the SwapRouter02 single-use fleet (fetched fingerprint) and unfetched >= 0.05 ETH SwapRouter02 buys to recipients in < 5 V3 pools.
'Pumped' = an operator buy at or after +W. Fisher exact test, Mantel-Haenszel by launch day. V-rule returns per group from s02 ($15).
-> s04_pumpgate356.out"""
import sys, os, json, pickle, statistics as S, collections as C
from math import comb
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
AN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis"
sys.path.insert(0, AN + "/V23/reaction_V3_tok_tok_97c7ba1b0d3f2de327f8c7b22abf2c27")
import rc
d = rc.load_all(); EV = d["EV"]
fam = json.load(open(AN + "/G3/opus/families.json"))["shapecode=89885b75fd29af13|d27d1e00|356|100|1|WETH|0.0000000"]
R = {r["pool"]: r for r in d["rows_all"]}
T356 = {x["p"]: x for x in pickle.load(open(os.path.join(HERE, "s02_trades.pkl"), "rb"))["T356"]}
NONOP = {"REUSED", "UNF-REUSED", "STRANGER", "MID", "SHAREDFP", "UNF-OTHER"}; PUMP = {"FLEET", "UNF-FLEETLIKE", "LW", "UNF-LW", "OPW", "UNF-OPW"}
X = {}
for p in fam:
    r = R[p]; L0 = r["launch_block"]; sw = []
    for s in EV[p]["sw"]:
        c, eoa, fp, fetched = rc.classify(r, s, d)
        sw.append((s[0] - L0, bool(s[2]), (s[3] if s[2] else s[12]) / 1e18, c, s[10]))
    X[p] = {"day": rc.day(r["launch_ts"]), "sw": sw}
def fisher(a, b, c, dd):
    n1, n2, k = a + b, c + dd, a + c; N = n1 + n2
    Pk = lambda x: comb(n1, x) * comb(n2, k - x) / comb(N, k); p0 = Pk(a)
    return sum(Pk(x) for x in range(max(0, k - n2), min(k, n1) + 1) if Pk(x) <= p0 * (1 + 1e-9))
L = []
def P(s=""): L.append(s); print(s)
P(f"356-B d27d1e00 value-0 launches: {len(X)}; with a V trade at $15: {sum(1 for p in X if p in T356)}")
cls = C.Counter(); eth = C.Counter()
for x in X.values():
    for off, buy, e, c, ltx in x["sw"]:
        if buy and 0 < off < 60 and not ltx: cls[c] += 1; eth[c] += e
P("buys at +1..+59 (outside the launch tx) by class (n, ETH): " + ", ".join(f"{c} {cls[c]} {eth[c]:.4f}" for c in sorted(cls, key=lambda c: -eth[c])))
mx = max((e for x in X.values() for off, buy, e, c, ltx in x["sw"] if buy and off < 60 and c in NONOP and not ltx), default=0)
P(f"largest non-operator buy before +60: {mx:.5f} ETH")
for days, lab in ((range(7), "all days"), ((5, 6), "days 6-7")):
    for W in (60,):
        for T in (0.0001, 0.0005, 0.001):
            a = b = c = dd = 0; excl = 0; strata = C.defaultdict(lambda: [0, 0, 0, 0]); grp = {"ey": [], "en": []}
            for p, x in X.items():
                if x["day"] not in days: continue
                pb = [off for off, buy, e, cl, ltx in x["sw"] if buy and cl in PUMP and not ltx]
                if pb and min(pb) < W: excl += 1; continue
                early = any(buy and cl in NONOP and e >= T and off < W and not ltx for off, buy, e, cl, ltx in x["sw"])
                pumped = any(off >= W for off in pb)
                k = (0 if early else 2) + (0 if pumped else 1); [a, b, c, dd][k]
                if early and pumped: a += 1
                elif early: b += 1
                elif pumped: c += 1
                else: dd += 1
                strata[x["day"]][k] += 1
                if p in T356: grp["ey" if early else "en"].append((pumped, T356[p]["ret"]))
            num = sum(s_[0] * s_[3] / sum(s_) for s_ in strata.values() if sum(s_)); den = sum(s_[1] * s_[2] / sum(s_) for s_ in strata.values() if sum(s_))
            mh = num / den if den else float("nan")
            P(f"{lab:9s} W +{W} T {T:<7}: early outside buy: {a+b:3d} pools, pumped {a:3d} ({a/max(1,a+b)*100:3.0f}%) | none: {c+dd:3d}, pumped {c:3d} ({c/max(1,c+dd)*100:3.0f}%) | "
              f"pumped before +{W} (excluded) {excl} | Fisher p {fisher(a, b, c, dd):.4f} | MH odds ratio by day {mh:.2f}")
            if T == 0.0005:
                for g, nm in (("ey", "with an early outside buy"), ("en", "without")):
                    v = grp[g]
                    if v: P(f"      V rule $15, {nm}: n {len(v)} mean {S.mean(r for _, r in v)*100:+.2f}% median {S.median(r for _, r in v)*100:+.3f}%")
# scenario: our +60 buy is an early outside buy; P(pump) drops to the 'early' rate; value per pumped / unpumped trade from the data
for days, lab in ((range(7), "all days"), ((5, 6), "days 6-7")):
    pumped = []; unp = []
    for p, x in X.items():
        if x["day"] not in days or p not in T356: continue
        pb = [off for off, buy, e, cl, ltx in x["sw"] if buy and cl in PUMP and not ltx and off >= 60]
        (pumped if pb else unp).append(T356[p]["ret"])
    P(f"{lab}: V trades in pools pumped at/after +60 n {len(pumped)} mean {S.mean(pumped)*100:+.2f}% | not pumped n {len(unp)} mean {S.mean(unp)*100:+.2f}% "
      f"| observed pump share {len(pumped)/(len(pumped)+len(unp))*100:.0f}%")
    for pr in (0.14, 0.12):
        m = pr * S.mean(pumped) + (1 - pr) * S.mean(unp)
        P(f"   if our buy cut the pump share to {pr*100:.0f}%: expected mean {m*100:+.2f}%")
open(os.path.join(HERE, "s04_pumpgate356.out"), "w").write("\n".join(L) + "\n")
