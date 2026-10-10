"""Residual risk after the protections: an ABRUPT operator speed-up (reaction <= 3 blocks) that no WARN saw coming. Loss = the stake of
the first of our full-stake A/B trades the operator reacts to, unless a canary reaction (which would show the new speed and drop us
to the minimum) comes first. f = P(our reacted trade comes before any canary event) for a jump at a uniformly random time, on the real
timeline (our trades: Oct 8 paper launches + Oct 9 live; canary events: the 11 outsider real-size buys followed by a pull within 60
blocks), each of our trades drawing a reaction with probability p_react (2 of our 10 A/B follow trades did). Then the expected cost per
day = q x f x S for a jump probability q per day, against the profit per day at MAX_TRADES_PER_DAY = 10 (Oct 8 paper means).
Also the exchangeability bound on the CURRENT regime: P(the next reaction is a new minimum) = 1/(n+1)."""
import sys, json, random, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import ladder_sim as LS
ev = LS.ev; HERE = LS.HERE
ES = json.load(open(HERE + "exits_stakes.json")); P = 2570.0
t0 = ev[0]["ts"] - 3600; t1 = ev[-1]["ts"]
def f_est(cap, p_react, fresh_excluded=True, n=20000, seed=1):
    rnd = random.Random(seed); trades = []; per = {}
    for e in ev:
        if e["kind"] != "trade" or (fresh_excluded and e["fresh"]): continue
        d = time.strftime("%m-%d", time.gmtime(e["ts"]))
        if cap and per.get(d, 0) >= cap: continue
        per[d] = per.get(d, 0) + 1; trades.append(e["ts"])
    can = sorted(e["ts"] for e in ev if e["kind"] == "canary")
    hit = tot = 0
    for _ in range(n):
        j = rnd.uniform(t0, t1)
        nxt_c = next((c for c in can if c > j), None)
        first_react = next((t for t in trades if t > j and rnd.random() < p_react), None)
        if first_react is None and nxt_c is None: continue
        tot += 1
        if first_react is not None and (nxt_c is None or first_react < nxt_c): hit += 1
    return hit / tot if tot else None
out = {"f": {}, "table": {}}
for cap in (10, None):
    for pr in (0.2, 1.0):
        f = f_est(cap, pr); out["f"][f"cap {cap} p_react {pr}"] = f
        print(f"f (our reacted full-stake trade before any canary), cap {cap}, p_react {pr}: {f:.2f}")
f_hi = max(out["f"].values())
print("\nstake | profit/trade | profit/day (10) | one catch | days of profit per catch | residual/day at q=1/30, 1/7 (f=%.2f) | break-even q/day" % f_hi)
for s in ("0.03", "0.1", "0.3", "1.0"):
    S = float(s); a = ES[f"{s}|T+1|V0"]["mean"]; pd = 10 * a * S * P
    r30 = (1 / 30) * f_hi * S * P; r7 = (1 / 7) * f_hi * S * P; be = pd / (f_hi * S * P)
    out["table"][s] = {"ret": a, "profit_trade_usd": a * S * P, "profit_day_usd": pd, "catch_usd": S * P, "days_per_catch": 1 / (10 * a), "trades_per_catch": 1 / a,
                       "residual_day_usd_q30": r30, "residual_day_usd_q7": r7, "breakeven_q_per_day": be}
    print(f"{s:5s} | ${a * S * P:6.2f} | ${pd:7.1f} | ${S * P:6.0f} | {1 / (10 * a):4.1f} | ${r30:6.1f}, ${r7:6.1f} | {be:.2f}")
# exchangeability bound on the current regime
allr = [5, 6, 6, 6, 6, 7, 7, 8, 11, 12, 13, 13, 14, 16, 16, 19, 23, 25, 41, 51]          # every reaction within 60 blocks (ours + outsiders), Oct 8-9
ab = [14, 16, 7, 11, 12, 13, 16, 19, 23, 25, 41, 51]                                     # on A/B launches only (ours 14, 16; outsiders)
print(f"\ncurrent regime, exchangeable lags: P(next reaction is a new minimum) all {1 / (len(allr) + 1):.3f} (n={len(allr)}), A/B launches {1 / (len(ab) + 1):.3f} (n={len(ab)})")
for s in ("0.03", "0.1", "0.3", "1.0"):
    S = float(s); a = ES[f"{s}|T+1|V0"]["mean"]
    b = 0.2 * (1 / (len(ab) + 1)) * S * P
    print(f"  {s}: per A/B trade <= 0.2 x {1 / (len(ab) + 1):.3f} x stake = ${b:.2f} (upper bound) vs profit ${a * S * P:.2f}")
    out["table"][s]["bound_per_trade_usd"] = b
json.dump(out, open(HERE + "residual.json", "w"), indent=1)
