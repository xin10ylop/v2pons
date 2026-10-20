"""Stage 8: what a $5 front earns on the current-regime pools of my slice (cur, 04:22..09:38 UTC) with the operator's reaction modelled.
Replay: analysis/R/common.py replay() (integer v4 maths): our buy of $5 (0.001946 ETH at $2,570) at the HEAD of block B, sold at the head of
block S, others' swaps in [B, S) re-applied, fee 1% each way, gas $0.02.
1. The candidate rule (fire on the first transaction touching the pool, its token or T's buyer at or after L+4, before T): its firing record
   on this slice (stage 4/6) decides its trades.
2. For scale, a hypothetical precursor with lead lam (event at T - lam) and engine latency dl (buy lands dl blocks after the event): B = T - lam + dl.
   The sell is sent on seeing the bot's buy at T and lands at S = T+1 (or T+2). Reaction: a pull lands at B + lag, lag = the minimum and the
   median pre-T lag measured in stage 5 (and REPORT_R's 3 / 5 if stage 5 has none). Pull at or before S: -100% (the same block counted lost;
   'opt' counts a pull in S's own block as survived). B > T: behind the bot (a back-run), replayed B..B+1, no reaction."""
import pickle, statistics as st, sys, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
CUR0 = 85553521
P = [p for p in pickle.load(open("parsed_mid.pkl", "rb"))["pools"] if p["L"] >= CUR0 and p["T"] is not None]
q = int(5 / USD * 1e18)
try:
    R5 = pickle.load(open("s5_reaction.pkl", "rb")); lags = sorted(r["lag"] for r in R5["pre"] if r["lag"] is not None)
except FileNotFoundError: lags = []
LMIN, LMED = (min(lags), pct(lags, .5)) if lags else (3, 5)
print(f"pools {len(P)}; $5 = {q/1e18:.6f} ETH; pre-T reaction lag from stage 5: n {len(lags)} min {LMIN} median {LMED}")
def sw_of(p): return [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
def L0(p):
    adds = [m for m in p["ml"] if m["dL"] > 0]; return adds[0]["dL"] if adds else 0
def run(p, B, S, pull):
    r = replay(sw_of(p), SQRT30, L0(p), B, S, q, 10000, 10000, pull)
    return r["ret"]
# 1. the candidate rule's own record
E = pickle.load(open("touch.pkl", "rb"))
rows = [r for r in E["rows"] if r["set"] == "cur"]
fire = {}
for r in sorted(rows, key=lambda r: (r["off"], r["ti"])):
    if r["pos"] != "before" or r["off"] < 4: continue
    if any(x.startswith(("pool:", "token:", "buyer:")) for x in r["touch"]) and r["pid"] not in fire: fire[r["pid"]] = r["off"]
print(f"\n1. the candidate rule fires (first pool/token/buyer touch at L+4..T, ahead of the bot's buy) in {len(fire)} of {len(P)} pools; trades 0 otherwise")
for pid, o in list(fire.items())[:10]:
    p = next(p for p in P if p["pid"] == pid); print(f"   fired at +{o}, T +{p['T']}, lead {p['T'] - o}")
# 2. a hypothetical precursor
print("\n2. a hypothetical precursor at T - lam, our buy landing dl blocks after it; mean / median / win / worst per trade, $ per trade")
def summ(v):
    return f"mean {100*st.mean(v):+7.2f}% median {100*st.median(v):+7.2f}% win {sum(1 for x in v if x > 0)/len(v):4.2f} worst {100*min(v):+7.1f}% ${5*st.mean(v):+.3f}/trade"
print(f"   no reaction, buy head of T (ahead of the bot), sell head of T+1: {summ([run(p, p['Tbn'], p['Tbn'] + 1, None) for p in P])}")
print(f"   no reaction, buy head of T-1, sell head of T+1:                 {summ([run(p, p['Tbn'] - 1, p['Tbn'] + 1, None) for p in P])}")
out = {}
for lam in (1, 2, 3, 4, 5, 6):
    for dl in (1, 2):
        for Sd in (1, 2):
            for lname, lag in (("min", LMIN), ("median", LMED)):
                for opt in (False, True):
                    v = []
                    for p in P:
                        B = p["Tbn"] - lam + dl; S = p["Tbn"] + Sd
                        if B > p["Tbn"]:          # landed behind the bot: a back-run sold one block later, no reaction modelled
                            v.append(run(p, B, B + 1, None)); continue
                        pull = B + lag
                        if pull < S or (pull == S and not opt): v.append(-1.0 - GAS_USD / 5)
                        else: v.append(run(p, B, S, None))
                    out[(lam, dl, Sd, lname, opt)] = v
for lname in ("min", "median"):
    lag = LMIN if lname == "min" else LMED
    print(f"\n   reaction: pull at our buy + {lag} ({lname} pre-T lag); sell lands at T+1 (T+2 in brackets); same-block pull counted lost [opt: survived]")
    for lam in (1, 2, 3, 4, 5, 6):
        for dl in (1, 2):
            v = out[(lam, dl, 1, lname, False)]; v2 = out[(lam, dl, 2, lname, False)]; vo = out[(lam, dl, 1, lname, True)]
            print(f"     lead {lam} latency {dl}: buy at T{dl - lam:+d} | {summ(v)} | [S=T+2: mean {100*st.mean(v2):+7.2f}%] [opt: mean {100*st.mean(vo):+7.2f}%]")
pickle.dump({"LMIN": LMIN, "LMED": LMED, "out": out, "fire": fire}, open("s8_front.pkl", "wb"))
