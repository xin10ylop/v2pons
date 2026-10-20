"""Skeptic 1, stage 7: the rule's $5 front with the pull lag drawn from the whole measured distribution (s4: the 27 outside non-dust buys
before T in the current regime: lags 3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,6,6,6,6,7,7,9,17,17,18,23), each trade averaged exactly over the 27 lags.
Our pools (s5, 116, every g) and the precursor angle's pools for g >= 40 (s6). Same outcome model and replay as s5."""
import pickle, json, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
LAGS = [3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 9, 17, 17, 18, 23]
SQRT30 = 679394651928963067279918579724198; NEW30 = 1791692539
Q = int(5 / USD * 1e18)
def prep(p, tb):
    p["Ttx"] = p.get("Ttx") or next(s["tx"] for s in p["sw"] if s["bot"])
    p["pullbn"] = min((m["bn"] for m in p["ml"] if m["dL"] < 0), default=None)
    adds = [m for m in p["ml"] if m["dL"] > 0]; p["L0"] = adds[0]["dL"] if adds else 0
    p["swl"] = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]; p["tb"] = tb
    return p
def rp(p, B, S): return replay(p["swl"], SQRT30, p["L0"], B, S, Q, 10000, 10000, p["pullbn"])["ret"]
def outcomes(p, g, lat, lat_s):
    """list of (kind, ret) over the 27 lags, or None for no trade"""
    T = p["Tbn"]; fire = next((b for b in p["tb"] if b >= p["L"] + g and b < T), None)
    if fire is None: return None
    l = fire + lat; out = []
    if l > T: r = rp(p, l, l + 1); return [("late", r)] * len(LAGS)
    sold = None
    for lag in LAGS:
        pull = l + lag
        if pull <= T: out.append(("pulled before T", -1.0 - GAS_USD / 5))
        elif T + lat_s >= pull: out.append(("pulled before our sell", -1.0 - GAS_USD / 5))
        else:
            if sold is None: sold = rp(p, l, T + lat_s)
            out.append(("front sold", sold))
    return out
def report(lab, S, g, lat, lat_s):
    allo = [o for o in (outcomes(p, g, lat, lat_s) for p in S) if o is not None]
    if not allo: print(f"  {lab} g {g:2d}: no trades"); return
    flat = [x for o in allo for x in o]; v = [x[1] for x in flat]; c = collections.Counter(x[0] for x in flat); n = len(LAGS)
    per = [st.mean(x[1] for x in o) for o in allo]
    print(f"  {lab} g {g:2d} lat {lat}/{lat_s}: trades {len(allo):3d}/{len(S)} | expected per trade: front sold {c['front sold']/n:5.1f}, pulled before T {c['pulled before T']/n:5.1f}, "
          f"pulled before sell {c['pulled before our sell']/n:5.1f}, late {c['late']/n:4.1f} | mean {100*st.mean(v):7.2f}% (${5*st.mean(v):+.2f}/trade), P(-100%) {100*sum(1 for x in v if x <= -0.99)/len(v):3.0f}%, "
          f"P(win) {100*sum(1 for x in v if x > 0)/len(v):3.0f}%; per-trade expectation p10/50/90 {100*pct(per,.1):.0f}/{100*pct(per,.5):.0f}/{100*pct(per,.9):.0f}%")
kb = KV("blk")
mine = [dict(p, slice="oldest") for p in pickle.load(open("parsed.pkl", "rb"))["pools"] if p["L"] < 85728798]
mine += [dict(p, slice="newest") for p in pickle.load(open("parsed_late.pkl", "rb"))["pools"] if p["L"] > 86150251]
mine = [p for p in mine if p["T"] is not None and p["ts"] >= NEW30]
tbs = {x["pid"]: x["tb"] for x in pickle.load(open("s5_triggers.pkl", "rb"))}
mine = [prep(p, tbs[p["pid"]]) for p in mine]
print(f"== this angle's pools (n {len(mine)}), the lag drawn from the 27 measured pre-T lags")
for lat, lat_s in ((1, 1), (2, 1), (2, 2)):
    for g in (1, 4, 10, 20, 30, 40, 45, 50): report("mine", mine, g, lat, lat_s)
blk = {}
with open("../precursor/cache/blk.jsonl") as f:
    for l in f:
        try: x = json.loads(l); blk[x["k"]] = x["v"]
        except Exception: pass
F = [p for p in pickle.load(open("../precursor/parsed.pkl", "rb"))["pools"] if p["line"] == "3.0" and p["T"] is not None]
for p in F:
    Ttx = next(s["tx"] for s in p["sw"] if s["bot"]); tb = []
    for b in range(p["Tbn"] - 12, p["Tbn"] + 1):
        x = blk.get(str(b))
        if x and any((t.get("to") or "").lower() == BOT and t["hash"] != Ttx and not (b == p["Tbn"] and int(t["transactionIndex"], 16) > p["Tti"]) for t in x["txs"]): tb.append(b)
    prep(p, tb)
print(f"\n== the precursor angle's pools (cached blocks [T-12, T+3]; only g with [L+g, T] covered)")
for lat, lat_s in ((1, 1), (2, 1)):
    for g in (40, 45, 50): report("finder", [p for p in F if p["Tbn"] - 12 <= p["L"] + g], g, lat, lat_s)
