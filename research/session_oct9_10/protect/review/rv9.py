"""residual.py's f re-run with the cooldown the design actually specifies: a canary WARN puts us at the minimum only until 3 CLEAN trades
(no reaction) in a row, then straight back to the saved rung. After an abrupt speed-up to <= 3 blocks, a reaction to a minimum-stake trade
is a cheap catch (halt), a reaction to a full-stake trade a full catch. f = P(full catch) over runs where a catch happens. Variants: all 11
canary events (as residual.py) or only the 5 the feed sees in time (value > 0); the canary as residual.py models it (safe forever) or with
the 3-clean-trade cooldown."""
import sys, json, random, time, io, contextlib
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
with contextlib.redirect_stdout(io.StringIO()):
    import ladder_sim as LS
PE = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/prot_eval.json"))
vis_keys = {(a["pid"], a["t"]) for a in PE["noncrowd_any_size"] if a["eth"] >= 2e-4 and a["value"] >= 2e-4 and a["lag"] is not None and a["lag"] <= 60}
ev = LS.ev
t0 = ev[0]["ts"] - 3600; t1 = ev[-1]["ts"]
def run(cap, p, C, visible_only, n=40000, seed=7):
    rnd = random.Random(seed); trades = []; per = {}
    for e in ev:
        if e["kind"] != "trade" or e["fresh"]: continue
        d = time.strftime("%m-%d", time.gmtime(e["ts"]))
        if cap and per.get(d, 0) >= cap: continue
        per[d] = per.get(d, 0) + 1; trades.append(("t", e["ts"]))
    cans = [("c", e["ts"]) for e in ev if e["kind"] == "canary" and (not visible_only or (e["pid"], time.strftime("%m-%d %H:%M:%S", time.gmtime(e["ts"]))) in vis_keys)]
    seq = sorted(trades + cans, key=lambda x: x[1])
    full = cheap = 0
    for _ in range(n):
        j = rnd.uniform(t0, t1); cool = 0; safe_forever = False; res = None
        for k, ts in seq:
            if ts <= j: continue
            if k == "c":
                if C is None: safe_forever = True; break
                cool = C; continue
            if rnd.random() < p:
                res = "cheap" if cool else "full"; break
            if cool: cool -= 1
        if safe_forever: cheap += 1
        elif res == "full": full += 1
        elif res == "cheap": cheap += 1
    return full / (full + cheap) if full + cheap else None, len(cans)
print("canary events visible:", len(vis_keys))
for cap in (10, None):
    for p in (0.2, 1.0):
        r = {}
        for vis in (False, True):
            for C in (None, 3):
                r[(vis, C)] = run(cap, p, C, vis)
        print(f"cap {cap} p_react {p}: all-11 safe-forever {r[(False, None)][0]:.2f} | all-11 3-clean cooldown {r[(False, 3)][0]:.2f} | "
              f"feed-visible-only ({r[(True, None)][1]}) safe-forever {r[(True, None)][0]:.2f} | feed-visible-only 3-clean cooldown {r[(True, 3)][0]:.2f}")
