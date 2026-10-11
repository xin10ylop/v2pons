"""Skeptic 1, stage 6: the only cells of s5 that did not lose were late arming (g 45-50: 2-7 trades of 116 pools, in sample). Re-run those
cells (g 40/45/50, same model and replay as s5) on the precursor angle's 200 pools (09:38-21:45 UTC), from its cached whole blocks [T-12, T+3]
(read only), where those blocks cover [L+g, T]. Also the candidate's precursor table on them restricted to d 1..12 (for a like-for-like
check of s5 Part A)."""
import pickle, json, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/R")
from common import replay, GAS_USD, USD
from lib import *
SQRT30 = 679394651928963067279918579724198
blk = {}
with open("../precursor/cache/blk.jsonl") as f:
    for l in f:
        try: x = json.loads(l); blk[x["k"]] = x["v"]
        except Exception: pass
P = [p for p in pickle.load(open("../precursor/parsed.pkl", "rb"))["pools"] if p["line"] == "3.0" and p["T"] is not None]
for p in P:
    p["Ttx"] = next(s["tx"] for s in p["sw"] if s["bot"])
    p["pullbn"] = min((m["bn"] for m in p["ml"] if m["dL"] < 0), default=None)
    adds = [m for m in p["ml"] if m["dL"] > 0]; p["L0"] = adds[0]["dL"] if adds else 0
    p["swl"] = [dict(bn=s["bn"], buy=s["buy"], q=s["q"], t=s["t"], sp=s["sp"], L=s["Lq"]) for s in p["sw"]]
    tb = []
    for b in range(p["Tbn"] - 12, p["Tbn"] + 1):
        x = blk.get(str(b))
        if x is None: continue
        for t in x["txs"]:
            if (t.get("to") or "").lower() != BOT or t["hash"] == p["Ttx"]: continue
            if b == p["Tbn"] and int(t["transactionIndex"], 16) > p["Tti"]: continue
            tb.append(b); break
    p["tb"] = sorted(set(tb))
occ = [sum(1 for p in P if p["Tbn"] - d in p["tb"]) for d in range(13)]
print(f"finder pools {len(P)}: pools with a tx to the bot router at d = 0..12 before T: {occ}; d 1..4 any: {sum(1 for p in P if any(1 <= p['Tbn']-b <= 4 for b in p['tb']))}")
Q = int(5 / USD * 1e18)
def rp(p, B, S): return replay(p["swl"], SQRT30, p["L0"], B, S, Q, 10000, 10000, p["pullbn"])["ret"]
def outcome(p, g, lat, lat_s, lag):
    T = p["Tbn"]; fire = next((b for b in p["tb"] if b >= p["L"] + g and b < T), None)
    if fire is None: return ("no trade", None)
    l = fire + lat
    if l <= T:
        pull = l + lag
        if pull <= T: return ("pulled before T", -1.0 - GAS_USD / 5)
        if T + lat_s >= pull: return ("pulled before our sell", -1.0 - GAS_USD / 5)
        return ("front sold", rp(p, l, T + lat_s))
    return ("late", rp(p, l, l + 1))
for lag in (3, 5, 9):
    for lat, lat_s in ((1, 1), (2, 1)):
        for g in (40, 45, 50):
            S = [p for p in P if p["Tbn"] - 12 <= p["L"] + g]     # blocks [L+g, T] cached
            o = [outcome(p, g, lat, lat_s, lag) for p in S]; v = [x[1] for x in o if x[1] is not None]; c = collections.Counter(x[0] for x in o)
            if not v: print(f"lag {lag} lat {lat}/{lat_s} g {g}: pools {len(S)}, no trades"); continue
            print(f"lag {lag} lat {lat}/{lat_s} g {g}: pools {len(S)}, trades {len(v)} | front sold {c['front sold']}, pulled before T {c['pulled before T']}, "
                  f"pulled before sell {c['pulled before our sell']}, late {c['late']} | mean {100*st.mean(v):.2f}% (${5*st.mean(v):+.2f}/trade), win {100*sum(1 for x in v if x > 0)/len(v):.0f}%")
