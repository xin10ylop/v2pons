"""Matched comparison of the operator's pull after its bot's first buy (T) in pools fronted by us vs pools fronted by others, same line, same
hours, same size class (>= 0.001 ETH ahead of T), same behaviour (the fronter sold within T-1..T+2, or did not sell before the pull),
and the pools where our own sell came BEFORE T (the Oct 10 afternoon exits on the decoys): was the pull still at T+3?"""
import json, pickle, collections, time
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
def hour(ts): g = time.gmtime(ts); return f"Oct{g.tm_mday} {g.tm_hour:02d}"
def pc(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))] if v else None
recs = []
for p in pools:
    if p["T"] is None: continue
    sw = p["sw"]; Tli = p["T_li"]; T = p["T"]
    ahead = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and (s["bn"], s["li"]) < Tli and s["q"] >= int(0.00003e18)]
    big = [s for s in ahead if s["q"] >= int(0.001e18)]
    if not big: continue
    us = [s for s in big if s["who"] == "ours"]
    f = us[0] if us else big[0]
    key = "ours" if f["who"] == "ours" else ("D65" if f["to"] == R65 else "DFD" if f["to"] == RFD else "other")
    fresh = f["nonce"] is not None and f["nonce"] <= 1
    sell = next((x for x in sw if not x["buy"] and ((x["who"] == "ours") if key == "ours" else x["eoa"] == f["eoa"])), None)
    srt = (sell["bn"] - (p["lb"] + T)) if sell else None
    recs.append({"line": p["line"], "hour": hour(p["ts"]), "period": p["period"], "fronter": key, "fresh": fresh, "with_us": bool(us), "q": f["q"] / 1e18, "off": f["off"],
                 "sell_rel_T": srt, "pull_rel_T": (p["pull"] - T) if p["pull"] is not None else None, "second": p["bot_buys"][1][0] - T if len(p["bot_buys"]) > 1 else None,
                 "n_big": len(big), "ts": p["ts"], "fee": p["fee"]})
json.dump(recs, open("x10_recs.json", "w"))
def stat(v):
    if not v: return "n    0"
    d = [r["pull_rel_T"] for r in v]
    k = lambda a, b: sum(1 for x in d if x is not None and a <= x <= b)
    sec = sum(1 for r in v if r["second"] is not None and (r["pull_rel_T"] is None or r["second"] < r["pull_rel_T"]))
    return f"n {len(v):4d} pulled <=T+3 {k(-99,3):4d} ({100*k(-99,3)/len(v):3.0f}%)  T+4..10 {k(4,10):3d}  T+11..60 {k(11,60):3d}  none by T+60 {len(v)-k(-99,60):4d}  bot 2nd buy {sec:4d}"
print("=== 2.433, hours where both we and another fronter (>= 0.001 ETH ahead of T) traded, pools WITHOUT us vs pools with us as the only big fronter")
hrs = sorted(set(r["hour"] for r in recs if r["line"] == "2.433"))
both = [h for h in hrs if any(r["hour"] == h and r["with_us"] for r in recs) and any(r["hour"] == h and not r["with_us"] for r in recs)]
print("hours with both:", both)
A = [r for r in recs if r["line"] == "2.433" and r["hour"] in both and r["with_us"] and r["n_big"] == 1]
B = [r for r in recs if r["line"] == "2.433" and r["hour"] in both and not r["with_us"]]
print("  ours alone          ", stat(A))
print("  others, no us       ", stat(B))
for sub, f in (("others that sold at T-1..T+2", lambda r: r["sell_rel_T"] is not None and -1 <= r["sell_rel_T"] <= 2), ("others that did not sell by the pull", lambda r: r["sell_rel_T"] is None or (r["pull_rel_T"] is not None and r["sell_rel_T"] > r["pull_rel_T"])),
               ("others 0.004-0.006 ETH", lambda r: 0.004 <= r["q"] <= 0.006), ("others fresh wallets", lambda r: r["fresh"]), ("others recurring wallets", lambda r: not r["fresh"])):
    v = [r for r in B if f(r)]
    if v: print(f"  {sub:36s}", stat(v))
print("  ours alone, our sell at T+1..T+2     ", stat([r for r in A if r["sell_rel_T"] is not None and 1 <= r["sell_rel_T"] <= 2]))
print("  ours alone, our sell BEFORE T        ", stat([r for r in A if r["sell_rel_T"] is not None and r["sell_rel_T"] < 0]))
AU = [r for r in recs if r["line"] == "2.433" and r["with_us"]]
for per in sorted(set(r["period"] for r in AU)):
    print(f"  {per} all our pools, our sell BEFORE T  ", stat([r for r in AU if r["period"] == per and r["sell_rel_T"] is not None and r["sell_rel_T"] < 0]))
    print(f"  {per} all our pools, our sell T+1..T+2  ", stat([r for r in AU if r["period"] == per and r["sell_rel_T"] is not None and 1 <= r["sell_rel_T"] <= 2]))
print("\n=== per hour, 2.433: ours alone vs others without us (pulled <= T+3 / n)")
for h in hrs:
    a = [r for r in recs if r["line"] == "2.433" and r["hour"] == h and r["with_us"]]
    b = [r for r in recs if r["line"] == "2.433" and r["hour"] == h and not r["with_us"]]
    f3 = lambda v: f"{sum(1 for r in v if r['pull_rel_T'] is not None and r['pull_rel_T'] <= 3)}/{len(v)}"
    fs = lambda v: f"{sum(1 for r in v if r['second'] is not None and (r['pull_rel_T'] is None or r['second'] < r['pull_rel_T']))}"
    print(f"  {h}: with us {f3(a):>8s} (2nd buy {fs(a):>3s})   others without us {f3(b):>8s} (2nd buy {fs(b):>3s})  others: {collections.Counter((r['fronter'], 'fresh' if r['fresh'] else 'recurring', round(r['q'],4)) for r in b).most_common(3)}")
print("\n=== 3.0: early buyers (>= 0.001 ETH ahead of T or no T), pull after their buy")
for r in sorted([r for r in recs if r["line"] == "3.0"], key=lambda r: r["ts"])[:0]: pass
v3 = [r for r in recs if r["line"] == "3.0"]
for per in sorted(set(r["period"] for r in v3)):
    for fr in sorted(set(r["fronter"] for r in v3 if r["period"] == per)):
        w = [r for r in v3 if r["period"] == per and r["fronter"] == fr]
        print(f"  {per} {fr:6s}", stat(w), "sizes", collections.Counter(round(r["q"], 4) for r in w).most_common(2), "sold T+k", collections.Counter(r["sell_rel_T"] for r in w).most_common(3))
