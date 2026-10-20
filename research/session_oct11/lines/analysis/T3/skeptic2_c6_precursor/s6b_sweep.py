"""Stage 6b: the same front, but the engine ignores the key until L+a (a = 1..50): it fires on the key's first occurrence at or after L+a.
'BLIND' fires at L+a whatever happens (the no-information baseline). A key carries timing information only if it beats BLIND at the same a.
Reaction as in s6 (lag 3 / 5 / the 26 measured lags); k = 1 and 2; s = 1. Outcome model and gains as in s6_front.py."""
import pickle, sys, collections, statistics as st, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
os.chdir(HERE)
D = pickle.load(open("s2_parsed.pkl", "rb")); P = {p["pid"]: p for p in D["pools"] if p["in_slice"] and p["T"] is not None}
E = pickle.load(open("s4_rows.pkl", "rb")); rows = E["rows"]
src = open("s5_keys.py").read(); exec(src[src.index("def keys(r):"): src.index("RCP_KEYS")])
LAGS = json.load(open(os.path.join(HERE, "..", "skeptic2_c4_presign", "s5_lags.json")))["pre_T_lags"]
Q = int(5 / USD * 1e18); G = {}
def gain(p, B, S):
    if (p["pid"], B, S) not in G:
        sw = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
        G[(p["pid"], B, S)] = replay(sw, SQRT30, p["L0"], B, S, Q, 10000, 10000, None)["ret"]
    return G[(p["pid"], B, S)]
occ = collections.defaultdict(lambda: collections.defaultdict(list))   # key -> pid -> sorted offsets where it occurs ahead of the bot's buy
for r in sorted(rows, key=lambda r: (r["off"], r["ti"])):
    if r["pos"] != "before" or r["off"] < 1: continue
    for k in set(keys(r) + xkeys(r)): occ[k][r["pid"]].append(r["off"])
RULES = ["BLIND", "ANY event in another line pool", "to+sel 0x00000000:fd9f1e10", "eth-send other->other", "cls other->other:a9059cbb",
         "cls other->other:095ea7b3", "X bot buy tx (bot router c1120e3d), another pool", "to+sel 0xb740ddd4:00000000"]
def outcome(p, b, k, s, lag):
    B = b + k; T = p["Tbn"]
    if B <= T: return -1.0 - GAS_USD / 5 if B + lag < T + s else gain(p, B, T + s)
    return gain(p, B, B + s)
def run(rk, a, k, s, lag):
    res = []
    for pid, p in P.items():
        if rk == "BLIND": offs = [a] if a < p["T"] or (a == p["T"]) else []
        else: offs = [o for o in occ[rk].get(pid, []) if o >= a]
        if not offs: continue
        b = p["L"] + offs[0]
        if b > p["Tbn"]: continue
        res.append(st.mean(outcome(p, b, k, s, l) for l in LAGS) if lag == "emp" else outcome(p, b, k, s, lag))
    return res
AS = [1, 10, 18, 20, 25, 30, 35, 40, 45, 50]
print(f"slice pools {len(P)}; mean return per trade (trades) of a $5 front, s = 1")
best = []
for k in (1, 2):
    for lag in (3, 5, "emp"):
        print(f"\n k {k} lag {lag}:  " + " ".join(f"{'a=' + str(a):>15}" for a in AS))
        for rk in RULES:
            cells = []
            for a in AS:
                r = run(rk, a, k, 1, lag)
                cells.append(f"{100*st.mean(r):+7.1f}% ({len(r):2d})" if r else f"{'-':>15}")
                if r: best.append((st.mean(r), len(r), rk, a, k, lag))
            print(f"   {rk[:38]:38s} " + " ".join(f"{c:>15}" for c in cells))
best.sort(key=lambda b: (b[0], b[1]), reverse=True)
print("\nhindsight-best cells on this slice (picked here, so optimistic), with >= 5 trades:")
for m, nn, rk, a, k, lag in [b for b in best if b[1] >= 5][:12]:
    print(f"   {rk[:45]:45s} a {a:2d} k {k} lag {lag!s:>3}: mean {100*m:+7.2f}% over {nn} trades, ${5*m:+.2f}/trade")
