"""Synthesizer step 6: what each line's edge is made of, as a probe statistic. For every trade of the rule (q $15, s02 replays): did a real
buy (>= 0.005 ETH, anyone; our wallet/relay never appear) land inside the hold [A, B)? Share of trades with one, by day, and the mean return
with / without. A probe that sees the share fall far below the census share has found the reaction (the operator or crowd stopped buying
behind us). -> s06_window_buys.out"""
import sys, os, json, pickle, statistics as S, collections as C
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "s02_lines.py")).read()
exec(src.split("# ---- overlaps")[0]); exec(src[src.index("def v3run"):src.index("def stats")])
L = []
def P(s=""): L.append(s); print(s)
s2_ = {k: set(v) for k, v in F2.items()}; s3_ = {k: set(v) for k, v in F3.items()}
v40 = (s2_[SH + "50.0900000"] | s2_[SH + "40.0900000"] | s2_[SH + "40.5900000"]) & s2_[K_70]
def wb3(p, A, B): return sum(s[3] for s in E3[p]["sw"] if s[2] and A <= s[0] < B and s[3] >= 5e15) / 1e18
def wb2(p, A, B): return sum(e[3] for e in E2[p]["ev"] if e[2] == "s" and e[3] > 0 and e[6] > 0 and A <= e[0] < B and e[3] >= 5e15) / 1e18
for lab, fn, wb, R, pools, a, b in (("V3 356-B K60 -> +260", v3run, wb3, R3, sorted(s3_[K_356]), 60, 260), ("V3 crowd K20 -> +80", v3run, wb3, R3, sorted(s3_[K_CROWD]), 20, 80),
                                   ("V2 fleet +20 -> +80", v2run, wb2, R2, sorted(s2_[K_FLEET]), 20, 80), ("V2 70adce63 >= 40 ETH +150 -> +250", v2run, wb2, R2, sorted(v40), 150, 250)):
    xs = fn(pools, a, b, 0.0058); byd = C.defaultdict(lambda: [0, 0]); w, wo = [], []
    for x in xs:
        r = R[x["p"]]; lb = r["launch_block"]; e = wb(x["p"], lb + a, lb + b); d = day(x["ts"]); byd[d][1] += 1
        if e > 0: byd[d][0] += 1; w.append(x["ret"])
        else: wo.append(x["ret"])
    P(f"{lab}: trades {len(xs)}; with a real buy inside the hold {len(w)} ({len(w)/len(xs)*100:.1f}%) mean {S.mean(w)*100:+.2f}% | without {len(wo)} mean {S.mean(wo)*100:+.2f}% median {S.median(wo)*100:+.3f}%")
    P("   share with a real buy in the hold by day: " + " ".join(f"d{d+1} {byd[d][0]}/{byd[d][1]}" if byd[d][1] else f"d{d+1} -" for d in range(7)))
open(os.path.join(HERE, "s06_window_buys.out"), "w").write("\n".join(L) + "\n")
