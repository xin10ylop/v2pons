"""The stake ladder and its warnings replayed on the real sequence: Oct 8's 46 follow launches priced by the verified pricer at every
stake (yday/follow_stakes.json, land1_fast = the current exit) and Oct 9's 9 live follow trades (returns at a stake s: Oct 8's mean at
s, since Oct 9 has no paper at other stakes), interleaved with the canary events (outsider real-size buys followed by a pull within
60 blocks, prot_eval.json) in time order.
Events: our trade with the pull at our buy + L (paper: the chain's pull; the 7 Oct 8 13:15-13:19 launches and the 9 Oct 9 trades:
the live lag) -> HALT if L <= 4 or the pull came at/before the sell; WARN (rung 0) if L <= 6; WATCH (no advance) if L <= 16; else
clean (advance after K clean trades in a row). Canary lag <= 6 -> WARN. Fresh trigger (nonce <= 3) -> the minimum stake for that
trade (the ladder state still updates). Prints the profit against a flat stake and the stake at each warning."""
import sys, json, statistics as st, time, calendar
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
SP = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
FS = json.load(open(SP + "yday/follow_stakes.json")); PE = json.load(open(HERE + "prot_eval.json")); LA = json.load(open(HERE + "live_all.json"))["trades"]
STK = ["0.0012", "0.004", "0.012", "0.03", "0.06", "0.1", "0.2", "0.3", "0.5", "1.0"]
oct8 = [r for r in FS["launches"] if r["results"]]
mean8 = {s: st.mean(r["results"][s]["land1_fast"]["ret"] for r in oct8) for s in STK}
trig_by_pid = {t["pid"]: t for t in PE["triggers"]}
live = {r["pid"]: r for r in LA}
ev = []
def ts_of(s): return calendar.timegm(time.strptime("2026-" + s, "%Y-%m-%d %H:%M:%S"))
for r in oct8:
    pid = r["pid"][:10]; t = trig_by_pid.get(pid)
    L = live[pid]["pull_after_buy"] if pid in live else r["results"]["0.1"]["land1_fast"]["pull_after_buy"]
    ev.append({"ts": calendar.timegm(time.strptime(r["time_utc"], "%Y-%m-%d %H:%M:%S")) + int(r["trigger_offset"] * 0.1025), "kind": "trade", "pid": pid,
               "ret": {s: r["results"][s]["land1_fast"]["ret"] for s in STK}, "L": L, "fresh": bool(t and t["nonce"] <= 3), "day": 8})
for r in LA:
    if r["utc"] >= "10-09 10:48" and r["trigger"]:
        ev.append({"ts": ts_of(r["utc"]), "kind": "trade", "pid": r["pid"], "ret": dict(mean8), "L": r["pull_after_buy"], "fresh": r["trigger"]["nonce"] <= 3, "day": 9,
                   "live_ret_0.0012": (r["eth_out"] - r["eth_in"]) / r["eth_in"]})
for a in PE["noncrowd_any_size"]:
    if a["eth"] >= 2e-4 and a["lag"] is not None and a["lag"] <= 60:
        ev.append({"ts": ts_of(a["t"]), "kind": "canary", "pid": a["pid"], "L": a["lag"]})
ev.sort(key=lambda e: e["ts"])


def run(rungs, K, cap_day=None, fresh_min=True, warn_lag=6, watch_lag=16, halt_lag=4, canary_warn=6, verbose=False):
    rung = 0; clean = 0; prof = 0.0; flat = 0.0; n = 0; per_day = {}; log = []; halted = None; resets = 0; at_risk_on_warn = []
    for e in ev:
        if halted: break
        if e["kind"] == "canary":
            if e["L"] <= canary_warn:
                at_risk_on_warn.append(("canary", time.strftime("%m-%d %H:%M", time.gmtime(e["ts"])), rungs[rung])); rung = 0; clean = 0; resets += 1
                log.append(f"{time.strftime('%m-%d %H:%M', time.gmtime(e['ts']))} canary lag {e['L']} -> WARN, stake {rungs[0]}")
            continue
        d = time.strftime("%m-%d", time.gmtime(e["ts"]))
        if cap_day and per_day.get(d, 0) >= cap_day: continue
        per_day[d] = per_day.get(d, 0) + 1; n += 1
        s = rungs[0] if (fresh_min and e["fresh"]) else rungs[rung]
        prof += float(s) * e["ret"][s]; flat += float(rungs[-1]) * e["ret"][rungs[-1]]
        L = e["L"]; tag = "clean"
        if L is not None and L <= 3:
            halted = (e["pid"], L, s); tag = "CAUGHT"
        elif L is not None and L <= halt_lag:
            halted = (e["pid"], L, s); tag = "HALT"
        elif L is not None and L <= warn_lag:
            at_risk_on_warn.append(("us", time.strftime("%m-%d %H:%M", time.gmtime(e["ts"])), s)); rung = 0; clean = 0; resets += 1; tag = "WARN"
        elif L is not None and L <= watch_lag:
            clean = 0; tag = "WATCH"
        else:
            clean += 1
            if clean >= K and rung < len(rungs) - 1:
                rung += 1; clean = 0
        log.append(f"{time.strftime('%m-%d %H:%M', time.gmtime(e['ts']))} {e['pid']} stake {s:>6s} ret {e['ret'][s]:+.4f} L {L} {tag} -> next rung {rungs[rung]}")
    if verbose:
        print("\n".join(log))
    return {"trades": n, "profit_eth": prof, "flat_profit_eth": flat, "kept": prof / flat if flat else None, "resets": resets, "halted": halted, "stake_at_warnings": at_risk_on_warn,
            "final_rung": rungs[rung]}


out = {"mean_ret_oct8_by_stake": mean8, "runs": {}}
print("Oct 8 paper mean return by stake (current exit):", {s: round(100 * v, 2) for s, v in mean8.items()})
print("events:", sum(1 for e in ev if e["kind"] == "trade"), "trades,", sum(1 for e in ev if e["kind"] == "canary"), "canary events")
for top, rungs in (("0.1", ["0.0012", "0.012", "0.03", "0.1"]), ("1.0", ["0.0012", "0.012", "0.03", "0.1", "0.3", "1.0"])):
    for K in (2, 3, 5):
        for cap in (None, 10):
            r = run(rungs, K, cap_day=cap)
            key = f"top {top} K {K} cap {cap}"
            out["runs"][key] = r
            print(f"{key:24s} trades {r['trades']:3d} profit {r['profit_eth']:.5f} ETH vs flat {r['flat_profit_eth']:.5f} ({100 * r['kept']:.0f}% kept) resets {r['resets']} halted {r['halted']} "
                  f"warn-stakes {r['stake_at_warnings']} final {r['final_rung']}")
    r = run(rungs, 3, cap_day=None, fresh_min=False); print(f"  (top {top} K 3, no fresh rule: profit {r['profit_eth']:.5f}, kept {100 * r['kept']:.0f}%, warn-stakes {r['stake_at_warnings']})")
    out["runs"][f"top {top} K 3 no fresh rule"] = r
print("\nTRACE top 1.0, K 3, no cap:")
run(["0.0012", "0.012", "0.03", "0.1", "0.3", "1.0"], 3, verbose=True)
# fresh rule alone: what it costs at a flat stake
for top in ("0.1", "1.0"):
    tr = [e for e in ev if e["kind"] == "trade"]
    flat = sum(float(top) * e["ret"][top] for e in tr); fr = sum(float(top) * e["ret"][top] - 0.0012 * e["ret"]["0.0012"] for e in tr if e["fresh"])
    print(f"fresh-trigger rule at flat {top}: forgoes {fr:.5f} ETH of {flat:.5f} ({100 * fr / flat:.1f}%) over {sum(1 for e in tr if e['fresh'])} fresh trades")
json.dump(out, open(HERE + "ladder_sim.json", "w"), indent=1, default=str)
