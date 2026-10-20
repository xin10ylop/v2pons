"""ladder_sim.py with the design finally proposed: a one-time RAMP (climb one rung after K clean trades in a row; WATCH resets the
count) and, after a WARN, a COOLDOWN (the minimum stake for the next C trades, then straight back to the rung held before the warning;
a WARN during the cooldown restarts it; only a clean trade counts it down, a WATCH holds it). HALT (L <= 4, or the pull at/before the sell) ends the run. Fresh trigger (nonce <= 3) -> the
minimum stake for that trade only. Same events as ladder_sim.py (it is imported)."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import ladder_sim as LS
ev = LS.ev


def run(rungs, K=3, C=3, cap_day=None, fresh_min=True, canary=True, start_top=False, verbose=False, budget=None):
    rung = len(rungs) - 1 if start_top else 0; clean = 0; cool = 0; saved = None
    prof = flat = 0.0; n = 0; per_day = {}; warns = []; log = []; halted = None
    for e in ev:
        if halted: break
        hm = time.strftime('%m-%d %H:%M', time.gmtime(e["ts"]))
        if e["kind"] == "canary":
            if canary and e["L"] <= 6:
                warns.append(("canary", hm, rungs[rung] if not cool else rungs[0]))
                if not cool: saved = rung
                cool = C; log.append(f"{hm} canary lag {e['L']} WARN")
            continue
        d = hm[:5]
        if cap_day and per_day.get(d, 0) >= cap_day: continue
        per_day[d] = per_day.get(d, 0) + 1; n += 1
        s = rungs[0] if (cool or (fresh_min and e["fresh"])) else rungs[rung]
        if budget is not None:                                                     # the stake at risk never above budget + profit banked
            allowed = budget + max(0.0, prof)
            s = max([x for x in rungs if float(x) <= allowed] or [rungs[0]], key=float) if float(s) > allowed else s
        prof += float(s) * e["ret"][s]; flat += float(rungs[-1]) * e["ret"][rungs[-1]]
        L = e["L"]; tag = "clean"
        if L is not None and L <= 4:
            halted = (hm, e["pid"], L, s); tag = "HALT"
        elif L is not None and L <= 6:
            warns.append(("us", hm, s)); tag = "WARN"
            if not cool: saved = rung
            cool = C
        else:
            if L is not None and L <= 16:
                clean = 0; tag = "WATCH"                                       # a reaction to us: the cooldown does not count down
            else:
                if cool:
                    cool -= 1
                    if cool == 0: rung = saved
                clean += 1
                if clean >= K and rung < len(rungs) - 1 and not cool:
                    rung += 1; clean = 0
        log.append(f"{hm} {e['pid']} stake {s:>6s} ret {e['ret'][s]:+.4f} L {L} {tag} cool {cool} rung {rungs[rung]}")
    if verbose: print("\n".join(log))
    return {"trades": n, "profit": prof, "flat": flat, "kept": prof / flat if flat else None, "warns": warns, "halted": halted, "final": rungs[rung]}


R01 = ["0.0012", "0.012", "0.03", "0.1"]; R1 = ["0.0012", "0.012", "0.03", "0.1", "0.3", "1.0"]
out = {}
for name, rungs in (("top 0.1", R01), ("top 1.0", R1)):
    for start_top in (False, True):
        for fresh in (True, False):
            for cap in (None, 10):
                r = run(rungs, fresh_min=fresh, cap_day=cap, start_top=start_top)
                k = f"{name} | {'already at top (ramp done)' if start_top else 'ramp from minimum'} | fresh rule {'on' if fresh else 'off'} | cap {cap}"
                out[k] = r
                print(f"{k:78s} trades {r['trades']:2d} profit {r['profit']:.5f} vs flat {r['flat']:.5f} kept {100 * r['kept']:5.1f}%  warns {[(w[0], w[1], w[2]) for w in r['warns']]} halted {r['halted']}")
for b in (0.03, 0.1):
    r = run(R1, start_top=True, budget=b)
    print(f"loss budget {b} ETH (stake <= budget + profit banked), rungs to 1.0: profit {r['profit']:.5f} vs flat 1.0 {r['flat']:.5f} kept {100 * r['kept']:.1f}%")
    out[f"budget {b}"] = r
print("\nTRACE top 1.0, ramp done, fresh rule on, no cap:")
run(R1, start_top=True, verbose=True)
json.dump(out, open(LS.HERE + "ladder_sim2.json", "w"), indent=1, default=str)
