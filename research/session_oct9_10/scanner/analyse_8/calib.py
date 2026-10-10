# calibration of the pricer on the controls: vbot-v2.433 (front) and operator-A (follow)
import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_8")
from common8 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
v = [p for p in P.values() if p["known"] == "vbot-v2.433"]
a = [p for p in P.values() if p["known"] == "operator-A"]
E = load_events({p["pid"] for p in v + a})
out = {}
# replay accuracy
errs = []
for p in v + a:
    po = Pool(p, E.get(p["pid"]), T, M)
    errs.append(po.check_replay())
errs.sort()
print("replay sqrtP rel err p50 %.2e p99 %.2e max %.2e" % (errs[len(errs)//2], errs[int(.99*len(errs))], errs[-1]))
out["replay_err"] = {"p50": errs[len(errs)//2], "p99": errs[int(.99*len(errs))], "max": errs[-1]}

def bot_first(po):
    for x in po.sw[:8]:
        if x["a0"] < 0 and bot_minout(po.tx(x)) is not None: return x
    return None

res = collections.defaultdict(list); cnt = collections.Counter(); per = []
for p in v:
    po = Pool(p, E.get(p["pid"]), T, M); L0 = po.L0
    if po.relay_swaps: cnt["relay_traded"] += 1
    fb = bot_first(po)
    # engine-like: the scheduled buy is the bot's router buy
    if fb is None: S = L0 + 20; cnt["no_bot_in_first8"] += 1
    elif fb["bn"] <= L0 + 1: cnt["bot_at_or_before_+1"] += 1; continue
    else: S = fb["bn"] + 1
    r = po.trade(L0 + 1, S)
    res["front_botrouter"].append(r); per.append((p["pid"], p["launch_block"], fb and fb["bn"] - L0, fb and -fb["a0"] / 1e18, r["exit"], r["ret"], bool(po.relay_swaps)))
    # generic: the first buy >= 0.0002 ETH at >= L0+2
    g = po.buys(REAL, after_bn=L0 + 1)
    S2 = g[0]["bn"] + 1 if g else L0 + 20
    res["front_generic"].append(po.trade(L0 + 1, S2))
    if po.relay_swaps: res["front_botrouter_relaypools"].append(r)
    else: res["front_botrouter_norelay"].append(r)
    # follow rule on v2.433
    t = po.buys(REAL)
    if t:
        B = t[0]["bn"] + 1; nb = po.buys(REAL, after_bn=B)
        S3 = min(nb[0]["bn"] + 1, B + 4) if nb else B + 4
        res["follow_generic"].append(po.trade(B, S3))
print(dict(cnt))
days = WINDOW_DAYS
for k, rs in res.items():
    rets = [r["ret"] for r in rs]; pf = sum(1 for r in rs if r["exit"] == "pulled_first"); ex = collections.Counter(r["exit"] for r in rs)
    s = stats(rets, pf, len(v) / days, len(v)); s["exits"] = dict(ex)
    s["dropped_bot"] = sum(1 for r in rs if r.get("dropped"))
    out["v2433_" + k] = s; print("v2.433", k, s)
# by period: before/after relay start (Oct 10 09:07 UTC = 1791623220)
for lab, cond in (("before_oct10_0907", lambda b: b < 1791623220), ("after", lambda b: b >= 1791623220)):
    rs = [x for x in per if cond(P[x[0]]["launch_ts"])]
    rets = [x[5] for x in rs]
    print(lab, stats(rets, sum(1 for x in rs if x[4] == "pulled_first")))
    out["v2433_front_" + lab] = stats(rets, sum(1 for x in rs if x[4] == "pulled_first"))
# operator A follow
res = collections.defaultdict(list)
for p in a:
    po = Pool(p, E.get(p["pid"]), T, M); L0 = po.L0
    t = po.buys(REAL)
    if t:
        B = t[0]["bn"] + 1; nb = po.buys(REAL, after_bn=B)
        S3 = min(nb[0]["bn"] + 1, B + 4) if nb else B + 4
        res["follow"].append(po.trade(B, S3))
        # hold-2 variant (sell lands at B+2)
        res["follow_hold2"].append(po.trade(B, B + 2))
    g = po.buys(REAL, after_bn=L0 + 1)
    S2 = g[0]["bn"] + 1 if g else L0 + 20
    res["front"].append(po.trade(L0 + 1, S2))
for k, rs in res.items():
    rets = [r["ret"] for r in rs]; pf = sum(1 for r in rs if r["exit"] == "pulled_first"); ex = collections.Counter(r["exit"] for r in rs)
    s = stats(rets, pf, len(a) / days, len(a)); s["exits"] = dict(ex)
    out["opA_" + k] = s; print("opA", k, s)
json.dump(out, open("calib.json", "w"), indent=1)
