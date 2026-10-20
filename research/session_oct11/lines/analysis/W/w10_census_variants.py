"""Census sensitivity of analyst C's V3 crowd-line rule to what the engine can actually do (7 days, 1,046 launches, stake 0.0058 ETH):
entry block (+1 = the engine's front fire at the end of the launch block, +2 = C's, +3); cap 60/70/80; the exit trigger = any buy >= 0.005 ETH
(C) or only a crowd-shaped buy (the value-0 call the engine would decode: selector 3593564c/484 B or a0193551 / 49f74a5d / 452 B to a
non-UR contract) or any buy the engine sees today (ETH value > 0 with the token in calldata) plus the crowd shape; WETH-as-token1 pools
(qs 1) skipped; per day; the last 24 h; and the share of the P&L in the top 10% of trades."""
import pickle, sys, os, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay, ETH_USD, GAS_USD
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb")); T = pickle.load(open(C + "/tx.pkl", "rb"))
L = [r for r in R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
T0 = 1791121962; Q = 0.0058; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
CROWD = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
def day(r): return min(6, int((r["launch_ts"] - T0) // 86400))
def buys(r):
    o = E[r["pool"]]; qs = r["quote_side"]
    return [(e[1] - o["lb"], e[7] if qs == 0 else e[8], e) for e in o["ev"] if e[0] == "s" and (e[7] if qs == 0 else e[8]) > 0]
def kind(e):
    t = T.get(e[-1])
    if not t: return "unfetched"
    if (t["selector"], t["calldata_len"]) in CROWD and (t["to"] or "") != UR: return "crowd"
    return "eth" if (t["value_wei"] or 0) > 0 else "val0"
def run(a, cap, trig_mode, skip_qs1=False, k=20, rows=L):
    xs = []
    for r in rows:
        if skip_qs1 and r["quote_side"] == 1: continue
        cand = []
        for off, dq, e in buys(r):
            if off < a or dq < 5e15: continue
            if trig_mode == "any": cand.append(off)
            else:
                kd = kind(e)
                if trig_mode == "crowd" and kd == "crowd": cand.append(off)
                if trig_mode == "seen" and kd in ("crowd", "eth"): cand.append(off)
        b = cand[0] + k if cand and cand[0] + k <= cap else cap
        x = replay(r, E[r["pool"]], a, b, Q)
        if x["ok"]: x["day"] = day(r); xs.append(x)
    return xs
def summ(lab, xs):
    rs = [x["ret"] for x in xs]; usd = [x["usd"] for x in xs]; srt = sorted(usd, reverse=True); top = sum(srt[:max(1, len(srt) // 10)]) / sum(usd) if sum(usd) else 0
    pd = " ".join(f"{st.mean([x['ret'] for x in xs if x['day'] == d])*100:+.1f}" for d in range(7))
    print(f"  {lab:<44} n {len(xs)} mean {st.mean(rs)*100:+.2f}% med {st.median(rs)*100:+.2f}% win {sum(v > 0 for v in rs)/len(rs):.2f} pulled {sum(x['pulled'] for x in xs)} "
          f"$/day {st.mean(usd)*len(xs)/7:+.0f} top10% share {top:.2f} | per day {pd}")
frb_kinds = {}
for r in L:
    bs = [(off, dq, e) for off, dq, e in buys(r) if dq >= 5e15]
    if bs: frb_kinds[kind(bs[0][2])] = frb_kinds.get(kind(bs[0][2]), 0) + 1
print(f"{len(L)} launches; the first real buy's kind: {frb_kinds}; qs 1 (WETH = token1): {sum(r['quote_side'] == 1 for r in L)}")
for a in (1, 2, 3):
    summ(f"entry +{a}, cap 80, trigger any >= 0.005", run(a, 80, "any"))
for cap in (60, 70, 80):
    summ(f"entry +1, cap {cap}, trigger any", run(1, cap, "any"))
summ("entry +1, cap 80, trigger crowd shape only", run(1, 80, "crowd"))
summ("entry +1, cap 80, trigger crowd + ETH-value calls", run(1, 80, "seen"))
summ("entry +1, cap 80, any, qs1 skipped", run(1, 80, "any", True))
summ("entry +1, cap 80, any, k=10", run(1, 80, "any", k=10))
summ("entry +1, cap 80, any, k=30", run(1, 80, "any", k=30))
