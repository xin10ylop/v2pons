#!/usr/bin/env python3
"""PM1444 v3.0 sample: bot vs outsider buys, sellers, the pull (who, through what, when, after which outsider buy), the hold-30 trades'
exits relative to the bot schedule. Reads cache_v3tx.pkl."""
import sys, os, json, pickle, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "v2_price.py")).read().split("B0 = 82878144")[0])
C = pickle.load(open(os.path.join(HERE, "cache_v3tx.pkl"), "rb")); TX = C["tx"]
V2 = json.load(open(os.path.join(HERE, "v2_price.json"))); H30 = {p: (ret, why, send) for p, ret, why, send in V2["v3"]["per_pool_hold30"]}
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
rows = []; botw = set(); sellers = collections.Counter(); pull_how = collections.Counter(); outs_all = []
for p in C["samp"]:
    r = R[p]; b0 = r["b0"]; pull = r.get("pull")
    ev = sorted(PL[p], key=lambda x: (x[0], x[1]))
    end = b0 + (pull if pull is not None and pull <= 600 else 600)
    buys = []; sells = []
    for bn, li, t0, snd, d, th in ev:
        if t0 != T_SWAP or bn > end: continue
        a0 = s128(W(d, 0)); t = TX.get(th)
        if t is None or abs(a0) < 2 * 10**14: continue
        (buys if a0 < 0 else sells).append((bn - b0, abs(a0) / 1e18, t))
    for o, a, t in buys:
        if t["to"] == BOT: botw.add(t["from"])
    out_b = [(o, a, t) for o, a, t in buys if t["to"] != BOT]
    for o, a, t in sells: sellers[("botwallet" if t["from"] in botw else "other", t["to"][:10])] += 1
    pt = None
    if pull is not None:
        pth = next((th for bn, li, t0, snd, d, th in ev if t0 == T_ML and sgn(W(d, 2)) < 0), None); pt = TX.get(pth)
        if pt: pull_how[(pt["from"] == r["from"].lower(), pt["to"][:10], pt["sel"], pt["nonce"] - r["nonce"])] += 1
    last_bot = max([o for o, a, t in buys if t["to"] == BOT] or [None]) if buys else None
    rows.append({"pid": p, "pull": pull, "n_bot": sum(1 for o, a, t in buys if t["to"] == BOT), "n_out": len(out_b), "out": [(o, round(a, 4), t["to"][:10], t["inlen"]) for o, a, t in out_b][:6],
                 "first_out": out_b[0][0] if out_b else None, "last_bot": last_bot, "h30": H30.get(p)})
print("sample", len(rows), "bot wallets", len(botw))
print("sells by", sellers.most_common(8))
print("pull (from deployer, to, sel, nonce - launch nonce):", pull_how.most_common(8))
print("pulled within 600:", sum(1 for x in rows if x["pull"] is not None and x["pull"] <= 600), "pull offsets", sorted(x["pull"] for x in rows if x["pull"] is not None and x["pull"] <= 600))
wo = [x for x in rows if x["n_out"] > 0]
print("pools with an outsider buy >= 0.0002 before pull/600:", len(wo), "of", len(rows))
for x in sorted(wo, key=lambda x: x["first_out"])[:40]:
    print("   ", x["pid"][:10], "first outsider +%s" % x["first_out"], x["out"][:3], "pull", x["pull"], "pull-after-outsider", (x["pull"] - x["first_out"]) if x["pull"] is not None else None, "last bot buy", x["last_bot"], "h30", x["h30"])
# reaction: compare pull timing with/without outsider
def pr(xs): 
    v = [x["pull"] for x in xs if x["pull"] is not None]
    return len(xs), len(v), sorted(v)[:10], (st.median(v) if v else None)
print("pull | outsider present:", pr(wo)); print("pull | no outsider:", pr([x for x in rows if x["n_out"] == 0]))
print("pull - last bot buy:", sorted((x["pull"] - x["last_bot"]) for x in rows if x["pull"] is not None and x["last_bot"] is not None and x["pull"] <= 600)[:40])
print("hold30 losers/pulled in sample:", [(x["pid"][:10], x["h30"], x["pull"], x["out"][:2]) for x in rows if x["h30"] and (x["h30"][1] == "pulled" or x["h30"][0] < 0)])
json.dump(rows, open(os.path.join(HERE, "v3_analyze.json"), "w"), indent=0)
