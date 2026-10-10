#!/usr/bin/env python3
"""The report's numbers from replay.py output (res.pkl) and reaction.json:
  python3 report.py res.pkl  -> report.json + text
Robust variant: for each (entry, TP, D) the mean over the four latencies (buy lands +1/+2, sell lands +1/+2), at each stake; the pick
maximises the WORST of (that mean, its neighbours' means: K or K' one step either side, D one step either side), at stake 0.0012."""
import sys, os, json, pickle, collections, statistics as st, time
HERE = os.path.dirname(os.path.abspath(__file__))
P = [p for p in pickle.load(open(sys.argv[1], "rb")) if not p.get("skip")]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "report.json")
STAKES = ("0.0012", "0.012", "0.03", "0.1")
ENT_F = ["K12", "K16", "K20", "K25"]; ENT_A = ["T+4", "T+8", "T+12", "T+16"]; TPS = ["tp0.01", "tp0.02", "tp0.03"]; DS = ["D34", "D38", "D42"]
LAT = [("b1", "s1"), ("b1", "s2"), ("b2", "s1"), ("b2", "s2")]


def stats(rs):
    v = [r["ret"] for r in rs if r and r.get("ret") is not None]
    if not v: return None
    ex = collections.Counter(r["exit"] for r in rs if r and r.get("ret") is not None)
    return {"n": len(v), "mean": round(st.mean(v), 5), "median": round(st.median(v), 5), "pos": sum(1 for x in v if x > 0), "worst": round(min(v), 4),
            "buy_reverted": ex.get("buy_reverted", 0), "pulled": ex.get("pulled", 0) + ex.get("pull_before_buy", 0), "tp": ex.get("tp", 0), "deadline": ex.get("deadline", 0),
            "no_trade": sum(1 for r in rs if r is None or r.get("ret") is None), "bot_buy_reverted": sum(1 for r in rs if r and r.get("bot_reverts"))}


def col(key, pools=None):
    return [p["R"].get(key) for p in (pools or P)]


def latmean(e, s, tp, D, pools=None):
    return st.mean(stats(col(f"{e}|{s}|{b}|{tp}|{D}|{sl}", pools))["mean"] for b, sl in LAT)


def bucket(p):
    g = time.gmtime(p["ts0"]); h = g.tm_hour // 6 * 6
    return time.strftime("%m-%d ", g) + "%02d-%02dh" % (h, h + 6)


def neighbours(e, D):
    fam = ENT_F if e in ENT_F else ENT_A; i = fam.index(e); j = DS.index(D)
    out = [(e, D)]
    if i > 0: out.append((fam[i - 1], D))
    if i < len(fam) - 1: out.append((fam[i + 1], D))
    if j > 0: out.append((e, DS[j - 1]))
    if j < len(DS) - 1: out.append((e, DS[j + 1]))
    return out


rep = {"n_pools": len(P), "pools_by_src": dict(collections.Counter(p["src"] for p in P))}
# data quality
rep["quality"] = {"replay_err_max": max(p["replay_err"] for p in P), "single_range_all": all(p["single_L"] for p in P),
                  "swaps_in_window_not_seen_by_feed": sum(len(p["unseen_swaps"]) for p in P),
                  "feed_amount_mismatch": sum(p["feed_amount_mismatch"] for p in P), "feed_events_without_swap": sum(p["feed_reverted"] for p in P),
                  "first_feed_buy_offset": dict(collections.Counter(p["first_feed_buy_off"] for p in P).most_common())}
# the grid at each stake, latency-averaged
grid = {}
for s in STAKES:
    for e in ENT_F + ENT_A:
        for tp in TPS:
            for D in DS:
                grid[f"{e}|{s}|{tp}|{D}"] = latmean(e, s, tp, D)
rep["grid_latency_mean"] = {k: round(v, 5) for k, v in grid.items()}
# robust pick at 0.0012
rob = []
for e in ENT_F + ENT_A:
    for tp in TPS:
        for D in DS:
            nb = [grid[f"{e2}|0.0012|{tp}|{D2}"] for e2, D2 in neighbours(e, D)]
            rob.append((min(nb), grid[f"{e}|0.0012|{tp}|{D}"], e, tp, D))
rob.sort(reverse=True)
rep["robust_rank"] = [{"entry": e, "tp": tp, "D": D, "latency_mean": round(m, 5), "worst_neighbour": round(w, 5)} for w, m, e, tp, D in rob[:12]]
best = rob[0]; BE, BTP, BD = best[2], best[3], best[4]
rep["best"] = {"entry": BE, "tp": BTP, "D": BD}
luck = max(grid.items(), key=lambda kv: kv[1] if "|0.0012|" in kv[0] else -9)
rep["luckiest_cell_0.0012"] = {"key": luck[0], "latency_mean": round(luck[1], 5)}
# the best variant in detail
det = {}
for s in STAKES:
    for b, sl in LAT:
        k = f"{BE}|{s}|{b}|{BTP}|{BD}|{sl}"; det[k] = stats(col(k))
    det[f"{BE}|{s}|b1|ideal"] = stats(col(f"{BE}|{s}|b1|ideal")); det[f"{BE}|{s}|b2|ideal"] = stats(col(f"{BE}|{s}|b2|ideal"))
    for side in ("buysonly", "stale4", "stale0", "tail"):
        det[f"{BE}|{s}|b1|{BTP}|{BD}|s1|{side}"] = stats(col(f"{BE}|{s}|b1|{BTP}|{BD}|s1|{side}"))
rep["best_detail"] = det
# per 6-hour bucket (best, stake 0.0012 and 0.1, b1 s1), and the cheap pricer on the same pools
bk = collections.defaultdict(list)
for p in P: bk[bucket(p)].append(p)
rep["per_6h"] = {}
for b in sorted(bk):
    ps = bk[b]
    row = {"pools": len(ps)}
    for s in ("0.0012", "0.1"):
        row[s] = stats(col(f"{BE}|{s}|b1|{BTP}|{BD}|s1", ps))
        row[s + "_latmean"] = round(latmean(BE, s, BTP, BD, ps), 5)
    cv = [p["cheap_hold30"]["ret"] for p in ps if p["cheap_hold30"]]
    row["cheap_hold30"] = {"n": len(cv), "mean": round(st.mean(cv), 5) if cv else None, "median": round(st.median(cv), 5) if cv else None}
    ex = [p["R"][f"{BE}|0.0012|b1|{BTP}|{BD}|s1"]["ret"] for p in ps if p["R"][f"{BE}|0.0012|b1|{BTP}|{BD}|s1"].get("ret") is not None and p["R"][f"{BE}|0.0012|b1|{BTP}|{BD}|s1"]["exit"] not in ("pulled", "pull_before_buy")]
    row["exact_excl_pulled_mean"] = round(st.mean(ex), 5) if ex else None
    rep["per_6h"][b] = row
# cheap vs exact, per pool
cmpk = f"{BE}|0.0012|b1|{BTP}|{BD}|s1"
diffs = []
for p in P:
    a = p["cheap_hold30"]; b_ = p["R"][cmpk]
    if a and b_ and b_.get("ret") is not None:
        diffs.append({"b0": p["b0"], "cheap": round(a["ret"], 5), "cheap_why": a["why"], "cheap_B": a["B"], "cheap_send": a["send"], "exact": round(b_["ret"], 5),
                      "exact_exit": b_["exit"], "exact_B": b_.get("B"), "exact_send": b_.get("send"), "diff": round(b_["ret"] - a["ret"], 5)})
cv = [p["cheap_hold30"]["ret"] for p in P if p["cheap_hold30"]]
rep["cheap_vs_exact"] = {"cheap_hold30_mean": round(st.mean(cv), 5), "cheap_hold30_median": round(st.median(cv), 5), "n": len(cv),
                         "exact_mean_same_pools": round(st.mean(d["exact"] for d in diffs), 5), "diff_mean": round(st.mean(d["diff"] for d in diffs), 5),
                         "diff_median": round(st.median(d["diff"] for d in diffs), 5), "abs_diff_lt_0.001": sum(1 for d in diffs if abs(d["diff"]) < 0.001),
                         "largest": sorted(diffs, key=lambda d: abs(d["diff"]), reverse=True)[:12]}
# stake effect: same pools, best variant, b1 s1, plus the gross price impact
rep["stake_effect"] = {s: stats(col(f"{BE}|{s}|b1|{BTP}|{BD}|s1")) for s in STAKES}
# reaction-adjusted: our buy is an outside buy; the deployer pulls `delay` blocks after it (empirical CDF, reaction_cdf.json: the first
# non-whitelisted outside buy >= 0.0001 ETH per pool, census + post-census). P(pull at or before our sell lands) = CDF(sell landing - B).
RC = os.path.join(HERE, "reaction_cdf.json")
if os.path.exists(RC):
    RCJ = json.load(open(RC)); cdfkey = "all/>=0.0001"
    delays = RCJ[cdfkey]["delays"]; N = RCJ[cdfkey]["n"]
    F = lambda h: sum(1 for d in delays if d <= h) / N
    rep["reaction"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("delays",)} for k, v in RCJ.items() if isinstance(v, dict) and "cdf" in v}
    rep["reaction_cdf_used"] = cdfkey
    def adjusted(key):
        vals = []
        for p in P:
            r = p["R"].get(key)
            if not r or r.get("ret") is None: continue
            if r["exit"] in ("buy_reverted", "pulled", "pull_before_buy"): vals.append(r["ret"]); continue
            sl = int(key.split("|")[5][1]) if len(key.split("|")) > 5 and key.split("|")[5][0] == "s" else 1
            hold = (r["send"] + sl) - r["B"]                       # blocks from our buy to our sell's landing
            q = F(hold)
            vals.append((1 - q) * r["ret"] + q * (-1.0))
        return round(st.mean(vals), 5) if vals else None
    adj = {}
    for k in sorted({k for p in P for k in p["R"]}):
        if k.endswith("ideal") or len(k.split("|")) != 6: continue
        adj[k] = adjusted(k)
    rep["reaction_adjusted_mean"] = adj
    rep["reaction_adjusted_top"] = sorted(((k, v) for k, v in adj.items() if v is not None), key=lambda kv: -kv[1])[:10]
    rep["reaction_adjusted_best_variant"] = {s: adj.get(f"{BE}|{s}|b1|{BTP}|{BD}|s1") for s in STAKES}
    # the seat variants without the reaction, for reference
    seat = {}
    for k in adj:
        if "|R" in k:
            seat[k] = {"no_reaction": stats(col(k)), "reaction_adjusted": adj[k]}
    rep["seat"] = seat
# stake 0.1: the bot's buy behind ours reverts if its quote did not see our buy; P(seen | blocks between) from stale2.py
PSEEN = {0: 0.0, 1: 0.17, 2: 0.2, 3: 0.29, 4: 0.53, 5: 0.86, 6: 0.98, 7: 0.92, 8: 0.71, 9: 0.5, 10: 0.89, 11: 0.75, 12: 0.84, 13: 0.93, 14: 0.8}
vals = []
for p in P:
    a = p["R"].get(f"{BE}|0.1|b1|{BTP}|{BD}|s1|stale0"); b_ = p["R"].get(f"{BE}|0.1|b1|{BTP}|{BD}|s1")
    if not a or a.get("ret") is None or not b_ or b_.get("ret") is None: continue
    g = a.get("gap_next_real_buy"); ps = 1.0 if g is None or g >= 15 else PSEEN.get(g, 0.9)
    vals.append(ps * a["ret"] + (1 - ps) * b_["ret"])
rep["stake_0.1_expected_with_P_seen"] = {"n": len(vals), "mean": round(st.mean(vals), 5) if vals else None}
json.dump(rep, open(OUT, "w"), indent=1, default=str)
# print
print(f"{len(P)} pools {rep['pools_by_src']}; quality {rep['quality']}")
print("robust ranking (stake 0.0012, latency-averaged mean, worst neighbour):")
for r in rep["robust_rank"][:8]: print("  ", r)
print("best", rep["best"], "| luckiest cell", rep["luckiest_cell_0.0012"])
for k, v in det.items(): print(f"  {k:40s} {v}")
print("per 6h:")
for b, r in rep["per_6h"].items():
    print(f"  {b} pools {r['pools']:3d} | 0.0012 b1s1 mean {r['0.0012']['mean']:+.4f} med {r['0.0012']['median']:+.4f} pos {r['0.0012']['pos']}/{r['0.0012']['n']} pulled {r['0.0012']['pulled']} rev {r['0.0012']['buy_reverted']} | latmean {r['0.0012_latmean']:+.4f} | 0.1 mean {r['0.1']['mean']:+.4f} botrev {r['0.1']['bot_buy_reverted']} | cheap {r['cheap_hold30']['mean']} | exact excl pulled {r['exact_excl_pulled_mean']}")
print("cheap vs exact:", {k: v for k, v in rep["cheap_vs_exact"].items() if k != "largest"})
for d in rep["cheap_vs_exact"]["largest"]: print("   ", d)
print("stake effect:"); [print("  ", s, v) for s, v in rep["stake_effect"].items()]
if "reaction" in rep:
    print("reaction CDF used", rep["reaction_cdf_used"], rep["reaction"].get(rep["reaction_cdf_used"]))
    print("reaction-adjusted top:", rep["reaction_adjusted_top"][:6])
    print("reaction-adjusted best variant:", rep["reaction_adjusted_best_variant"])
    for k, v in sorted(rep["seat"].items()):
        if "|0.0012|" in k: print("  seat", k, "no reaction mean", v["no_reaction"]["mean"] if v["no_reaction"] else None, "med", v["no_reaction"]["median"] if v["no_reaction"] else None, "adjusted", v["reaction_adjusted"])
print("stake 0.1 with P(seen):", rep["stake_0.1_expected_with_P_seen"])
