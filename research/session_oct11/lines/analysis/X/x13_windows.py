"""The reaction table by the windows of the two days (UTC), not by 6-hour period: pools by who bought >= 0.001 ETH (or any non-dust
amount) ahead of the bot's first buy, pulled by T+3 / T+10, the bot's 2nd buy before the pull."""
import pickle, calendar, collections
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
t = lambda d, h, m: calendar.timegm((2026, 10, d, h, m, 0))
W = [("Oct10 00:00-09:08 (before our first trade)", t(10, 0, 0), t(10, 9, 8)), ("Oct10 09:08-11:40 (we trade at +1)", t(10, 9, 8), t(10, 11, 40)),
     ("Oct10 11:40-13:38 (we are off: daily cap)", t(10, 11, 40), t(10, 13, 38)), ("Oct10 13:38-17:37 (we trade)", t(10, 13, 38), t(10, 17, 37)),
     ("Oct10 17:37-24:00 (feed blocked: we are gone)", t(10, 17, 37), t(11, 0, 0)), ("Oct11 00:00-14:26 (we are off)", t(11, 0, 0), t(11, 14, 26)),
     ("Oct11 14:26-15:32 (we trade at +2, fee 2500)", t(11, 14, 26), t(11, 15, 32)), ("Oct11 15:32-16:07 (fee 5000, we refuse it)", t(11, 15, 32), t(11, 16, 7)),
     ("Oct11 16:07-16:52 (we trade 0.0058/0.0097)", t(11, 16, 7), t(11, 16, 52)), ("Oct11 16:52-17:58 (we are dry)", t(11, 16, 52), t(11, 17, 58)),
     ("Oct11 17:58-23:11 (we trade 0.002/auto)", t(11, 17, 58), t(11, 23, 12))]
def cls(p):
    Tli = p["T_li"]
    ahead = [s for s in p["sw"] if s["buy"] and s["who"] in ("ours", "w") and (Tli is None or (s["bn"], s["li"]) < Tli) and (Tli is not None or s["off"] <= 60) and s["q"] >= int(0.00003e18)]
    if any(s["who"] == "ours" for s in ahead): return "us"
    big = [s for s in ahead if s["q"] >= int(0.001e18)]
    if big:
        s = big[0]; return ("others >= 0.001 (" + ("0x65050a9b" if s["to"] == R65 else "0xfd1b271f" if s["to"] == RFD else "other router") + (", fresh wallet" if (s["nonce"] or 0) <= 1 else "") + ")")
    if ahead: return "others < 0.001 only"
    return "nobody"
print("| window (UTC) | line | who bought ahead of the bot | pools | no bot buy | pulled <= T+3 | <= T+10 | not by T+60 | bot's 2nd buy before the pull |")
print("|---|---|---|---|---|---|---|---|---|")
for lab, a, b in W:
    for line in ("2.433", "3.0"):
        v = [p for p in pools if p["line"] == line and a <= p["ts"] < b]
        if not v: continue
        c = collections.defaultdict(list)
        for p in v: c[cls(p)].append(p)
        for k in sorted(c, key=lambda k: -len(c[k])):
            w = c[k]; wt = [p for p in w if p["T"] is not None]
            k3 = sum(1 for p in wt if p["pull"] is not None and p["pull"] - p["T"] <= 3); k10 = sum(1 for p in wt if p["pull"] is not None and p["pull"] - p["T"] <= 10)
            n60 = sum(1 for p in wt if p["pull"] is None or p["pull"] - p["T"] > 60)
            sec = sum(1 for p in wt if len(p["bot_buys"]) > 1 and (p["pull"] is None or p["bot_buys"][1][0] < p["pull"]))
            if line == "3.0" and k == "nobody" and k3 == 0: print(f"| {lab} | 3.0 | nobody | {len(w)} | {len(w)-len(wt)} | 0 | {k10} | {n60} | {sec} |"); continue
            print(f"| {lab} | {line} | {k} | {len(w)} | {len(w)-len(wt)} | {k3} | {k10} | {n60} | {sec} |")
