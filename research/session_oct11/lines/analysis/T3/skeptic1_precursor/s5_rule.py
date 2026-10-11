"""Skeptic 1, stage 5: candidate 1 re-measured on pools the finder did not use (current regime only, launched from 04:22:19 UTC: the oldest
slice 04:22-09:38 UTC with L < 85,728,798 and the newest slice 21:31-22:36 UTC with L > 86,150,251).
Candidate: "a transaction to the bot router 0x1cbaf24d (any selector, any other pool), seen in the feed: buy so that it lands 1-2 blocks later".
Part A: is there a peak? Per pool, d = Tbn - b for every block b in [L+1, Tbn] holding a tx to 0x1cbaf24d (not the pool's own T buy; in block T
         only txs ahead of the bot's, d = 0); pools with one at d = 0..12, the background share of blocks holding one (L+4..T-5 and L+4..T-13),
         the 4-block-window expectation 1-(1-r)^4, the nearest trigger's lead (smallest d >= 1), per selector too.
Part B: the rule as an engine runs it: armed from L+g, it fires on the first block b >= L+g (b < Tbn) holding a tx to the bot router; our buy
         lands at b+lat (lat 1 or 2). If no trigger before Tbn the engine sees the bot's buy first: no trade.
         Outcome with the operator's reaction (s4: pull lag after an outside buy before T, current regime n 27: min 3, median 5):
           landing l < Tbn: pull at l+lag; if l+lag <= Tbn the bot never buys (27 of 27 pre-T buys) -> -100%; else the bot buys at T, our sell
             lands at Tbn+lat_s; sold if Tbn+lat_s < l+lag (replay), else -100%;
           l == Tbn: optimistic = ahead of the bot's tx (front, sold at Tbn+lat_s, pull at l+lag); pessimistic = behind (late);
           l > Tbn: late buy behind the bot, sold at l+1 (post-T lag >= 9: no pull) -> replay.
         Replay: analysis/R/common.py replay (integer v4 maths), $5 stake (q = 5/2570 ETH), fee 1% both legs, gas $0.02; our buy at the
         head of block l (ahead of every other swap in l), sold at the head of the sell block; the bot's buy assumed to fill (optimistic)."""
import pickle, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
NEW30 = 1791692539; FIRST_FINDER = 85728798; LAST_FINDER = 86150251
P = [dict(p, slice="oldest") for p in pickle.load(open("parsed.pkl", "rb"))["pools"] if p["L"] < FIRST_FINDER]
P += [dict(p, slice="newest") for p in pickle.load(open("parsed_late.pkl", "rb"))["pools"] if p["L"] > LAST_FINDER]
P = sorted([p for p in P if p["T"] is not None and p["ts"] >= NEW30], key=lambda p: p["L"])
kb = KV("blk")
print(f"pools: {len(P)} (oldest slice {sum(1 for p in P if p['slice']=='oldest')}, {utc(min(p['ts'] for p in P if p['slice']=='oldest'))}-{utc(max(p['ts'] for p in P if p['slice']=='oldest'))} UTC; "
      f"newest {sum(1 for p in P if p['slice']=='newest')}, {utc(min(p['ts'] for p in P if p['slice']=='newest'))}-{utc(max(p['ts'] for p in P if p['slice']=='newest'))} UTC)")
Ts = [p["T"] for p in P]
print(f"T (bot's first buy, blocks after L): p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)}, min {min(Ts)}, max {max(Ts)}; within +-1 of the median: {sum(1 for t in Ts if abs(t-st.median(Ts))<=1)}/{len(Ts)}")
# ---- Part A
def trig_blocks(p, selp=None):
    """block -> list of (selector, from) of txs to the bot router (not p's own T buy; block T: only ahead of it)"""
    out = {}
    for b in range(p["L"] + 1, p["Tbn"] + 1):
        blk = kb.d[str(b)]
        for t in blk["txs"]:
            if (t.get("to") or "").lower() != BOT or t["hash"] == p["Ttx"]: continue
            if b == p["Tbn"] and int(t["transactionIndex"], 16) > p["Tti"]: continue
            sel = t["input"][2:10]
            if selp and sel != selp: continue
            out.setdefault(b, []).append((sel, t["from"].lower()))
    return out
selc = collections.Counter()
for p in P:
    for b, v in trig_blocks(p).items():
        for s, f in v: selc[s] += 1
print("\ntxs to the bot router in [L+1, T] of these pools, by selector:", dict(selc.most_common()))
def partA(label, selp=None, S=P):
    occ = [0] * 13; bgh = bgn = 0; bgh13 = bgn13 = 0; nearest = []; w14 = 0
    for p in S:
        tb = trig_blocks(p, selp)
        for d in range(13):
            if p["Tbn"] - d in tb: occ[d] += 1
        for b in range(p["L"] + 4, p["Tbn"] - 4):
            bgn += 1; bgh += b in tb
        for b in range(p["L"] + 4, p["Tbn"] - 12):
            bgn13 += 1; bgh13 += b in tb
        ds = sorted(p["Tbn"] - b for b in tb if p["Tbn"] - b >= 1)
        nearest.append(ds[0] if ds else None)
        w14 += any(1 <= d <= 4 for d in ds)
    r = bgh / bgn if bgn else 0; r13 = bgh13 / bgn13 if bgn13 else 0
    exp = len(S) * (1 - (1 - r) ** 4)
    near = [x for x in nearest if x is not None]
    nc = collections.Counter(min(x, 13) for x in near)
    print(f"\n[{label}] n {len(S)}: pools with a trigger at d = 0..12 before T: {occ}")
    print(f"   background: {100*r:.1f}% of blocks L+4..T-5 hold one ({bgh}/{bgn}); {100*r13:.1f}% of L+4..T-13 ({bgh13}/{bgn13}); per-d expectation {len(S)*r:.1f} pools")
    print(f"   pools with one anywhere in d 1..4: {w14} ({100*w14/len(S):.0f}%), expected by chance {exp:.1f} ({100*exp/len(S):.0f}%); ratio {w14/exp if exp else 0:.2f}")
    print(f"   peak d in 1..4: d={1+occ[1:5].index(max(occ[1:5]))} {max(occ[1:5])} pools vs mean of d 5..12 {sum(occ[5:13])/8:.1f}")
    print(f"   nearest trigger before T (smallest d >= 1): " + ", ".join(f"d{k if k < 13 else '13+'} {v}" for k, v in sorted(nc.items())) + f"; none in [L+1,T-1]: {sum(1 for x in nearest if x is None)}")
    return r
r_all = partA("ANY tx to the bot router (the candidate)")
for s, _ in selc.most_common(4): partA(f"selector {s} only", s)
partA("oldest slice only", S=[p for p in P if p["slice"] == "oldest"]); partA("newest slice only", S=[p for p in P if p["slice"] == "newest"])
# ---- Part B
Q = int(5 / USD * 1e18)
def swl(p): return [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
for p in P:
    adds = [m for m in p["ml"] if m["dL"] > 0]; p["L0"] = adds[0]["dL"] if adds else 0; p["swl"] = swl(p)
    p["tb"] = sorted(trig_blocks(p))
def rp(p, B, S):
    r = replay(p["swl"], SQRT30, p["L0"], B, S, Q, 10000, 10000, p["pullbn"])
    return r["ret"]
SQRT30 = 679394651928963067279918579724198
def outcome(p, g, lat, lat_s, lag, same_block_ahead=True):
    T = p["Tbn"]; fire = next((b for b in p["tb"] if b >= p["L"] + g and b < T), None)
    if fire is None: return ("no trade", None, None)
    l = fire + lat
    if l < T or (l == T and same_block_ahead):
        pull = l + lag
        if pull <= T: return ("pulled before T", -1.0 - GAS_USD / 5, T - fire)
        if T + lat_s >= pull: return ("pulled before our sell", -1.0 - GAS_USD / 5, T - fire)
        return ("front sold", rp(p, l, T + lat_s), T - fire)
    lb = max(l, T + 1)   # a buy behind the bot's in block T is replayed as a buy at the head of T+1 (the replay buys at a block head only)
    return ("late", rp(p, lb, lb + 1), T - fire)
def run(S, g, lat, lat_s, lag, ahead=True):
    o = [outcome(p, g, lat, lat_s, lag, ahead) for p in S]
    tr = [x for x in o if x[0] != "no trade"]; v = [x[1] for x in tr if x[1] is not None]
    c = collections.Counter(x[0] for x in o)
    return c, v, [x[2] for x in tr]
def show(lab, c, v, n):
    if not v: print(f"  {lab}: no trades ({dict(c)})"); return
    m = st.mean(v)
    print(f"  {lab}: trades {len(v):3d}/{n} | front sold {c['front sold']:3d}, pulled before T {c['pulled before T']:3d}, pulled before our sell {c['pulled before our sell']:3d}, "
          f"late {c['late']:3d}, no trade {c['no trade']:3d} | mean {100*m:7.2f}% (${5*m:+.2f}/trade), median {100*st.median(v):6.2f}%, win {100*sum(1 for x in v if x>0)/len(v):3.0f}%, "
          f"-100% {100*sum(1 for x in v if x <= -0.99)/len(v):3.0f}%")
print("\n== Part B: the rule run as an engine, $5 front; reaction = pull at our buy + lag (lag from s4: min 3, median 5; 9 = our own probe)")
print("   'g' = blocks after L from which the engine arms (the literal rule: g = 1); lat = blocks from the trigger to our buy landing; lat_s = from the bot's buy to our sell")
for lag in (3, 5, 9):
    for lat, lat_s in ((1, 1), (2, 1), (2, 2)):
        print(f"\n -- lag {lag}, buy lands trigger+{lat}, sell lands T+{lat_s}; buy in block T counted AHEAD of the bot (optimistic)")
        for g in (1, 4, 10, 15, 18, 20, 25, 30, 35, 40, 45, 50):
            c, v, lead = run(P, g, lat, lat_s, lag); show(f"g {g:2d}", c, v, len(P))
print("\n -- no reaction at all (lag 1000), lat 1/1, optimistic: the most the rule could earn")
for g in (1, 10, 20, 30, 40):
    c, v, lead = run(P, g, 1, 1, 1000); show(f"g {g:2d}", c, v, len(P))
print("\n -- pessimistic ordering (a buy landing in block T sits behind the bot's), lag 5, lat 1/1")
for g in (1, 10, 20, 30, 40):
    c, v, lead = run(P, g, 1, 1, 5, False); show(f"g {g:2d}", c, v, len(P))
# lead-time of the literal rule's fire (T - trigger block)
for g in (1, 20):
    c, v, lead = run(P, g, 1, 1, 5)
    lead = [x for x in lead if x is not None]
    print(f"\nlead of the rule's fire (Tbn - trigger block), g {g}: n {len(lead)}, p10/50/90 {pct(lead,.1)}/{pct(lead,.5)}/{pct(lead,.9)}, "
          f"share in 1..2: {sum(1 for x in lead if 1<=x<=2)}, 3..4: {sum(1 for x in lead if 3<=x<=4)}, >4: {sum(1 for x in lead if x>4)}; histogram " + str(sorted(collections.Counter(min(x, 30) for x in lead).items())))
# in-time front gain if a front lands exactly at T-1 / T (head), sold at T+1 (the ceiling of a perfect rule)
for B in (-2, -1, 0):
    v = [rp(p, p["Tbn"] + B, p["Tbn"] + 1) for p in P]; v = [x for x in v if x is not None]
    print(f"perfect front: buy head of T{B:+d}, sell head of T+1, no reaction: n {len(v)} mean {100*st.mean(v):.2f}% median {100*st.median(v):.2f}% min {100*min(v):.2f}%")
v = [rp(p, p["Tbn"] + 1, p["Tbn"] + 2) for p in P]; v = [x for x in v if x is not None]
print(f"late buy: head of T+1 behind the bot, sold head of T+2: n {len(v)} mean {100*st.mean(v):.2f}% median {100*st.median(v):.2f}%")
pickle.dump([{k: p[k] for k in ("pid", "L", "T", "Tbn", "slice", "tb")} for p in P], open("s5_triggers.pkl", "wb"))
