"""Census reaction test (task 3): pools where a stranger bought after the bot's first buy T and before its 2nd buy (or T+60) vs pools without;
the pull's offset after T. Stranger = a tx-identified wallet that is not a bot wallet, not ours, not a repeat actor (>= 20 line pools), not the
sentinel. Repeat actors' buys after T are reported separately. Compared within line x regime x day. Every stranger case listed in r08_cases.txt."""
import pickle, collections, json
from common import *
P = pickle.load(open("cpools.pkl", "rb"))
def grp(p):
    if p["line"] == "3.0": return "3.0 d%d" % p["day"] + ("" if p["day"] < 6 else (" new" if p["ts"] >= NEW30 else " old"))
    return "2.433 d%d" % p["day"]
rows = []; cases = []
for p in P:
    if p["T"] is None or p["ours"]: continue
    T = p["T"]; sw = p["sw"]
    bots = [s for s in sw if s["who"] == "bot" and s["off"] > T]
    end = bots[0]["off"] if bots else T + 60
    win = [s for s in sw if s["buy"] and T < s["off"] < end or (s["buy"] and s["off"] == T and s["who"] != "bot" and sw.index(s) > sw.index(next(x for x in sw if x["who"] == "bot")))]
    strangers = [s for s in win if s["who"] == "x" and s["eoa"] != SENTINEL]
    reps = [s for s in win if s["who"] == "rep"]
    unk = [s for s in win if s["who"] in ("x?", "r?")]
    pullT = None if p["pull"] is None else p["pull"] - T
    rows.append({"g": grp(p), "line": p["line"], "str": bool(strangers), "rep": bool(reps), "unk": bool(unk), "pullT": pullT, "span": p["ev_to_off"] - T,
                 "first_str": strangers[0]["off"] - T if strangers else None})
    for s in strangers:
        cases.append(f"{grp(p):12s} {utc(p['ts'])} pool {p['pool'][:12]} T +{T} stranger {s['eoa'][:10]} to {s['to'][:10]} buy {s['q']/1e18:.6f} at T+{s['off']-T} | 2nd bot buy T+{(bots[0]['off']-T) if bots else '-'} | pull T+{pullT}")
open("r08_cases.txt", "w").write("\n".join(cases) + "\n")
def stat(rs):
    v = [r["pullT"] for r in rs]
    k = lambda d: sum(1 for x in v if x is not None and x <= d)
    pr = [x for x in v if x is not None]
    return f"n {len(rs):4d} pulled<=T+10 {k(10):4d} <=T+30 {k(30):4d} <=T+60 {k(60):4d} <=T+400 {k(400):4d} ({100*k(400)/max(1,len(rs)):5.1f}%) pull-T p50 {pct(pr,.5)}"
print("pools without our wallet, with T; stranger = tx-identified one-off wallet buying after T before the bot's 2nd buy")
for g in sorted(set(r["g"] for r in rows), key=lambda x: (x.split()[0], x)):
    R = [r for r in rows if r["g"] == g]
    A = [r for r in R if r["str"]]; Bn = [r for r in R if not r["str"] and not r["rep"]]; Rp = [r for r in R if r["rep"] and not r["str"]]
    print(f"{g:12s} STRANGER {stat(A)}\n{'':12s} none     {stat(Bn)}\n{'':12s} repeat   {stat(Rp)}")
for line in ("2.433", "3.0"):
    R = [r for r in rows if r["line"] == line and not r["g"].endswith(" old") and r["g"] != "2.433 d6"]
    A = [r for r in R if r["str"]]; Bn = [r for r in R if not r["str"] and not r["rep"]]
    print(f"{line} all days except the pull-at-T+3 phase: STRANGER {stat(A)}\n{'':48s}none     {stat(Bn)}")
print(len(cases), "stranger buys listed in r08_cases.txt")
# who are the strangers after T (by wallet / router), sizes
c = collections.Counter(l.split(" stranger ")[1].split(" buy ")[0] for l in cases)
print("top stranger (eoa, to):", c.most_common(12))
