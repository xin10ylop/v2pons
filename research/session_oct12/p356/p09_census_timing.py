"""p09: the p08 grid on census 2's launches of the same launcher code (Oct 4 13:52 .. Oct 11 13:52 UTC; scratchpad cache, no network), as an
out-of-sample look at p08's later exits on the value launches (5 of the 48 h value launches are also in the census: Oct 10 11:24 .. Oct 11
13:52). By census day too, for the one cell asked about. -> p09_census_timing.out"""
import sys, os, json, pickle, statistics as S, collections as C
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as K
SCR = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2"
sys.path.insert(0, SCR + "/census")
from load import load_events
F = json.load(open(SCR + "/analysis/G3/opus/families.json"))
R = {r["pool"]: r for r in pickle.load(open(SCR + "/analysis/G3/opus/v3rows.pkl", "rb"))}
lc = F["lc=89885b75|d27d1e00"]; E = load_events(set(lc))
FROM_TS = 1791121962
OVER = set(x["pool"] for x in K.launches())
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
groups = {"census v0 356-B value 0": [p for p in lc if R[p]["launch"]["calldata_len"] == 356 and int(R[p]["launch"]["value_wei"]) == 0],
          "census value launches (len != 356)": [p for p in lc if R[p]["launch"]["calldata_len"] != 356]}
def run(p, a, b, q=0.0058):
    o = {"lb": R[p]["launch_block"], "ev_to": E[p]["ev_to"], "ev": E[p]["ev"]}
    return K.trade({"pool": p}, o, a, b, q)
for g, ps in groups.items():
    P(f"\n{g} (n {len(ps)}; also in the 48 h set: {sum(1 for p in ps if p[2:] in OVER)}): mean / median / win % / pulled, $15 net of gas")
    P("  buy\\sell " + " ".join(f"{b:>27d}" for b in (160, 260, 360, 460, 600, 1000)))
    for a in (1, 60, 200):
        cells = []
        for b in (160, 260, 360, 460, 600, 1000):
            if b <= a: cells.append(f"{'-':>27s}"); continue
            rs = [run(p, a, b) for p in ps]; rs = [r for r in rs if r and r.get("ok")]; rt = [r["ret"] for r in rs]
            cells.append(f"{S.mean(rt)*100:+8.1f} {S.median(rt)*100:+6.2f} {sum(1 for v in rt if v > 0)/len(rt)*100:4.0f} {sum(r['pulled'] for r in rs):3d}")
        P(f"  +{a:<4d}    " + " ".join(cells))
    for b in (260, 600):
        byd = C.defaultdict(list)
        for p in ps:
            r = run(p, 60, b)
            if r and r.get("ok"): byd[min(6, int((R[p]["launch_ts"] - FROM_TS) // 86400))].append(r["ret"])
        P(f"  buy +60 sell +{b} by census day: " + " | ".join(f"d{d+1} n {len(byd[d])} {S.mean(byd[d])*100:+.1f}%" for d in range(7) if byd[d]))
open(K.J("p09_census_timing.out"), "w").write("\n".join(L) + "\n")
