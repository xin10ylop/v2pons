"""calibration 1: every live front trade of Oct 10 (front_audit/full_audit.json) re-priced by common14.replay at its own stake, buy and
sell blocks; calibration 2: the front rule by period (the live window vs the whole census)"""
import sys, json, statistics as st, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14")
from common14 import *
A = json.load(open("/home/user/v2pons/research/session_oct9_10/front_audit/full_audit.json"))
P0 = load_pools()
pref = {}
for p in P0.values(): pref.setdefault(p["pid"][:10], []).append(p["pid"])
pids = set()
for a in A:
    for x in pref.get(a["pid"], []): pids.add(x)
ctx = Ctx(pids)
rows = []
for a in A:
    c = pref.get(a["pid"])
    if not c or len(c) != 1 or a.get("ret") is None: continue
    p = ctx.P[c[0]]
    if p["known"] != "vbot-v2.433": continue
    lb = p["launch_block"]
    r = replay(ctx, p, lb + a["buy_off"], lb + a["sell_off"], X=int(round(a["stake"] * 1e18)))
    if r.get("ret") is None: continue
    rows.append((a["ret"], r["ret"], a["stake"], a["pid"], a["sell_off"], a["bot_off"], r["exit"], a["pulled_first"]))
d = [m - l for l, m, *_ in rows]
print("matched", len(rows), "live mean %.4f model mean %.4f | diff mean %.5f median %.5f p5 %.5f p95 %.5f max|d| %.4f" % (
    st.mean(r[0] for r in rows), st.mean(r[1] for r in rows), st.mean(d), st.median(d), sorted(d)[len(d)//20], sorted(d)[19*len(d)//20], max(abs(x) for x in d)))
for r in sorted(rows, key=lambda r: -abs(r[1] - r[0]))[:8]: print("  worst", r)
json.dump({"n": len(rows), "live_mean": st.mean(r[0] for r in rows), "model_mean": st.mean(r[1] for r in rows), "diff_median": st.median(d),
           "diff_mean": st.mean(d), "rows": rows}, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14/calib.json", "w"), default=str)
