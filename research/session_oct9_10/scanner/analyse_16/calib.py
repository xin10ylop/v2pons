"""controls: (1) the v2.433 front rule on every census v2.433 pool (sell one block after the bot's first router buy, else launch + 20);
(2) every live front trade of Oct 10 (front_audit/full_audit.json) re-priced at its own stake, buy and sell offsets; (3) operator A follow;
(4) the v2.433 capacity from the bot's real minOut (word 4)"""
import sys, json, statistics as st, collections, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16")
from common16 import *
P0 = load_pools()
V = [p for p in P0.values() if p["known"] == "vbot-v2.433"]
A = [p for p in P0.values() if p["known"] == "operator-A"]
AUD = json.load(open("/home/user/v2pons/research/session_oct9_10/front_audit/full_audit.json"))
pref = collections.defaultdict(list)
for p in P0.values(): pref[p["pid"][:10]].append(p["pid"])
ctx = Ctx([p["pid"] for p in V + A])


def bot_sched(ctx, p, B):
    for s in buys(ctx, p):
        if s["bn"] > B and is_bot_buy(ctx.tx(s["tx"])): return s
    return None


def real_sched(ctx, p, B):
    for s in buys(ctx, p):
        if s["bn"] > B and -s["a0"] >= MIN_REAL: return s
    return None


out = {}
# (1) v2.433 front
rs = [front(ctx, p, bot_sched) for p in V]
out["v2433_front_all"] = summ(rs)
live0, live1 = 84880000, 84970000   # ~Oct 10 09:05 .. 11:40 UTC
rs_live = [r for p, r in zip(V, rs) if live0 <= p["launch_block"] <= live1]
out["v2433_front_livewindow"] = summ(rs_live)
with_bot = [r for r in rs if r["sched"] is not None and r["sched"] < 20]
out["v2433_front_botbuy_by_20"] = summ(with_bot)
out["v2433_exits"] = dict(collections.Counter(r["exit"] for r in rs))
out["v2433_sched_offsets_p10_50_90"] = pct([r["sched"] for r in rs if r["sched"] is not None])
out["v2433_no_bot_buy"] = sum(1 for r in rs if r["sched"] is None)
out["v2433_front_generic_sched"] = summ([front(ctx, p, real_sched) for p in V])
print("v2.433 front all       ", fmt(out["v2433_front_all"]))
print("v2.433 front live win  ", fmt(out["v2433_front_livewindow"]))
print("v2.433 bot buy by +20  ", fmt(out["v2433_front_botbuy_by_20"]))
print("v2.433 generic sched   ", fmt(out["v2433_front_generic_sched"]))
print("exits", out["v2433_exits"], "sched offs", out["v2433_sched_offsets_p10_50_90"], "no bot buy", out["v2433_no_bot_buy"])
# (2) live audit re-priced
rows = []
for a in AUD:
    c = pref.get(a["pid"])
    if not c or len(c) != 1 or a.get("ret") is None: continue
    p = ctx.P[c[0]]
    if p["known"] != "vbot-v2.433" or p["pid"] not in ctx.E: continue
    lb = p["launch_block"]
    r = replay(ctx, p, lb + a["buy_off"], lb + a["sell_off"], X=int(round(a["stake"] * 1e18)))
    if r.get("ret") is None: continue
    rows.append((a["ret"], r["ret"], a["stake"], a["pid"], a["sell_off"], a["bot_off"], r["exit"], a["pulled_first"]))
d = [m - l for l, m, *_ in rows]
out["live_audit"] = {"n": len(rows), "live_mean": st.mean(r[0] for r in rows), "model_mean": st.mean(r[1] for r in rows),
                     "diff_mean": st.mean(d), "diff_median": st.median(d), "diff_abs_p95": sorted(abs(x) for x in d)[int(0.95 * len(d))],
                     "max_abs_diff": max(abs(x) for x in d), "worst": sorted(rows, key=lambda r: -abs(r[1] - r[0]))[:5]}
print("live audit: matched %d live mean %+.4f model mean %+.4f diff mean %+.5f median %+.5f |d| p95 %.5f max %.4f" % (
    len(rows), out["live_audit"]["live_mean"], out["live_audit"]["model_mean"], out["live_audit"]["diff_mean"], out["live_audit"]["diff_median"],
    out["live_audit"]["diff_abs_p95"], out["live_audit"]["max_abs_diff"]))
for w in out["live_audit"]["worst"]: print("   worst", w)
# (3) operator A follow and front
fa = [follow(ctx, p) for p in A]; fa = [r for r in fa if r]
out["opA_follow"] = summ(fa); out["opA_follow_exits"] = dict(collections.Counter(r["exit"] for r in fa))
out["opA_follow_trig_p10_50_90"] = pct([r["trig"] for r in fa])
out["opA_front_generic"] = summ([front(ctx, p, real_sched) for p in A])
print("operator A follow      ", fmt(out["opA_follow"]), out["opA_follow_exits"], "trig", out["opA_follow_trig_p10_50_90"])
print("operator A front       ", fmt(out["opA_front_generic"]))
# (4) v2.433 capacity from the bot's minOut
caps = []
for p in V:
    sb = bot_sched(ctx, p, p["launch_block"])
    if not sb: continue
    c = capacity(ctx, p, sb)
    if c: caps.append((c["cap_eth"], c["Y_eth"], c["minout_over_quote"]))
out["v2433_capacity_eth_p10_50_90"] = pct([c[0] for c in caps])
out["v2433_minout_over_launchquote_p10_50_90"] = pct([c[2] for c in caps])
c05 = [c[0] for c in caps if abs(c[1] - 0.05) < 0.002]
out["v2433_capacity_for_0.05_buy"] = pct(c05)
print("v2.433 capacity p10/50/90", out["v2433_capacity_eth_p10_50_90"], "minOut/quote", out["v2433_minout_over_launchquote_p10_50_90"], "0.05 ETH buys", out["v2433_capacity_for_0.05_buy"], len(c05))
json.dump(out, open(OUT + "/calib.json", "w"), indent=1, default=str)
