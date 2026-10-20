#!/usr/bin/env python3
"""base_v2_results.py: the Base V2 line (src/base_v2_engine.py, service flip-base-v2; docs/BASE_V2.md) in one screen, from its log
(BASE_V2_LOG_PATH, /var/log/flip/base_v2.jsonl, and the rotated copies): the service, the release, dry or live, the stage settings in
force (the stake and its cap, the positions at once, the buys a day, the band, the hard exit, the take profit, the daily stop and the
halts, as the last start line logged them), the feeds (the last flow line), the window's creations by tier (seen, tradable, watched,
skipped with the top why), the guard's verdicts and their time, the fires and their ready_ms, the outsiders and the pulls, the trades
dry and live (count, win rate, mean return, ETH and dollars, the exits) and the last 10, the stage-0 gate (three correct decisions) and
the stage-1 rule, the halt (HALTED.base_v2), the day's stops and the tiers ended, the open positions (base_v2_positions.json), the
wallet's and the relay's ETH (read from the RPC; the key file is never opened), and the alarms.

    sudo python3 ~/v2pons/deploy/base_v2_results.py           # the last 24 hours
    sudo python3 ~/v2pons/deploy/base_v2_results.py 72        # the last 72 hours
    sudo python3 ~/v2pons/deploy/base_v2_results.py --alerts  # trouble only (nothing when all is well): the halt, a hung reader, a position held too long, the day's stop, a tier ended, the roster missing or stale, the relay short, the last alarm
"""
import collections, json, os, statistics, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_v2_wallet as BV                                                              # standard library only at import: the system python runs this
BW = BV.BW

ALERTS = sys.argv[1:2] == ["--alerts"]
try:
    HOURS = float(sys.argv[1]) if len(sys.argv) > 1 and not ALERTS else 24
except ValueError:
    sys.exit(__doc__.split("\n\n")[1])
LOG = BV.log_path()
LAST = 10
NOT_READING_S = 180                                                                      # no flow line (one a minute) this long while active: the reader hangs
POSITION_OLD_S = 480                                                                     # a position open this long is past the hard exit (+180 blocks, 360 s) and the wall-clock fallback (370 s)
GATE_N = 3                                                                               # stage 0: three correct decisions (docs/BASE_V2.md section 9)
SEEN_MAX_MS, GUARD_MAX_MS, READY_MAX_MS = 1000, 1000, 1500                               # section 9's limits: seen within 1 s, the guard under 1 s, ready under 1.5 s
RIGHT_WHY = ("value outside the band", "excluded tier")                                  # a watched tier's refusal
CAUSE_WHY = ("guard", "outsider before our fire", "pulled before our fire")              # a tolerant-tier pair refused for a cause of its own
STAGE1_FIRST = 5
ROSTER_STALE_DAYS = 2
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
pct = lambda r: "%+.1f%%" % (100 * r)
short = lambda x: (str(x)[:10] + "…") if x else "-"
W = 120


def num(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def read_logs(hours):
    """the events in the window (oldest first), and the last start and flow lines whenever they were"""
    ev = BV.read_log(LOG, hours); last = {}
    for e in BV.read_log(LOG, None, evs=("start", "flow")):
        last[e["ev"]] = e
    return ev, last.get("start", {}), last.get("flow", {})


def cfg(st, skey, ekey, default, scale=None):
    """a setting as the start line logged it (the engine's own name and unit; `scale` divides it), else the env file (its BASE_V2_ name), else the default"""
    s = st.get("settings") if isinstance(st.get("settings"), dict) else {}
    if s.get(skey) is not None:
        return num(s[skey]) / scale if scale else s[skey]
    v = BV.setting(ekey)
    return default if v is None else v


def count(xs, f, top=None):
    c = collections.Counter(str(f(e)) for e in xs)
    return "; ".join("%s x%d" % kv for kv in c.most_common(top)) or "none"


def stats(xs):
    if not xs:
        return "%5d  %5s  %10s" % (0, "-", "-")
    return "%5d  %4.0f%%  %10s" % (len(xs), 100 * sum(1 for r in xs if r > 0) / len(xs), pct(sum(xs) / len(xs)))


def ms_line(xs, limit):
    xs = [num(x) for x in xs if x is not None]
    if not xs:
        return "no times"
    return "ms median %.0f, max %.0f (under %s: %d of %d)" % (statistics.median(xs), max(xs), format(limit, ","), sum(1 for x in xs if x <= limit), len(xs))


def balances(st):
    """the wallet's and the relay's ETH, from the RPC (BASE_V2_RPC_URL, else BASE_V2_READ_ALT_URL); only the host is printed"""
    out = []; stake = num(cfg(st, "STAKE_ETH_WEI", "BASE_V2_STAKE_ETH", 0.02, 1e18), 0.02); usd = num(cfg(st, "ETH_USD", "BASE_V2_ETH_USD", 2570), 2570)
    for name, k in (("wallet", "BASE_V2_WALLET"), ("relay ", "BASE_V2_RELAY")):
        addr = (BV.setting(k) or st.get(k[8:].lower()) or "")
        if not addr or not str(addr).startswith("0x"):
            out.append("%s: %s not set" % (name, k)); continue
        try:
            b = int(BW.rpc("eth_getBalance", [addr, "latest"], timeout=8), 16) / 1e18
            out.append("%s %s: %.6f ETH ($%.2f)%s" % (name, addr, b, b * usd, (" = %.1f stakes of %g ETH" % (b / stake, stake)) if k == "BASE_V2_RELAY" and stake else ""))
        except Exception as ex:
            out.append("%s %s: balance not read (%s)" % (name, addr, str(ex)[:80]))
    return out


def position_state():
    """(the open positions' texts, the file's age in seconds) from base_v2_positions.json; ([], None) when there is none"""
    p = BV.positions_file()
    try:
        pos = BW.open_positions(); age = time.time() - os.path.getmtime(p) if os.path.exists(p) else None
    except SystemExit as ex:
        return [str(ex)], None
    return pos, age


def roster_state():
    """(count, age in days) of the roster file; (None, None) without one"""
    try:
        d = json.load(open(BV.roster_file())); ws = d.get("wallets") if isinstance(d, dict) else None
        return (len(ws) if isinstance(ws, list) else None), (time.time() - os.path.getmtime(BV.roster_file())) / 86400
    except Exception:
        return None, None


def today_stops(ev):
    day = time.strftime("%Y-%m-%d", time.gmtime())
    return [e for e in ev if e["ev"] == "stop" and str(e.get("day")) == day and e.get("what") in ("day", "tier")]


def alerts():
    ev, st, fl = read_logs(3); now = time.time(); out = []; live = BW.live_setting()
    hf = BV.halt_file()
    if os.path.exists(hf):
        try:
            why = open(hf).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        out.append("BASE V2 HALTED: %s (no new buy; an open position is still sold; deploy/base_v2_results.py has the rest)" % why)
    seen = max(fl.get("t") or 0, st.get("t") or 0)
    if now - seen > NOT_READING_S and BW.service_active():
        out.append("BASE V2 NOT READING: %s while flip-base-v2 is active (journalctl -u flip-base-v2 -n 30)"
                   % (("no flow line for %.0f min" % ((now - seen) / 60)) if seen else "no flow line in " + LOG))
    pos, age = position_state()
    if pos and (age is None or age > POSITION_OLD_S):
        out.append("BASE V2 POSITION OPEN %s: %s (a position lives 180 blocks at most, 6 minutes; look at the relay on basescan)"
                   % (("for %.0f s since the file's last change" % age) if age is not None else "", "; ".join(p[:120] for p in pos)))
    for e in today_stops(ev):
        out.append("BASE V2 %s: %s; new buys resume at 00:00 UTC" % ("STOPPED FOR THE DAY" if e.get("what") == "day" else "TIER %s ENDED FOR THE DAY" % e.get("tier"), str(e.get("reason"))[:150]))
    if live:
        n, days = roster_state()
        if n is None:
            out.append("BASE V2 ROSTER MISSING: %s is not a roster (base_v2_roster.py builds it; a live start refuses without it)" % BV.roster_file())
        elif days is not None and days > ROSTER_STALE_DAYS:
            out.append("BASE V2 ROSTER STALE: built %.1f days ago (the cron runs base_v2_roster.py at 00:20 UTC: /var/log/flip/base_v2_roster.log)" % days)
        stake = num(cfg(st, "STAKE_ETH_WEI", "BASE_V2_STAKE_ETH", 0.02, 1e18), 0.02); margin = num(cfg(st, "MARGIN_WEI", "BASE_V2_RELAY_MARGIN_ETH", 0.0005, 1e18), 0.0005)
        if fl.get("relay_eth") is not None and num(fl["relay_eth"]) < stake + margin:
            out.append("BASE V2 RELAY SHORT: %.6f ETH, under the stake + margin %g: no buy until it is funded (base_v2_ops.py deposit)" % (num(fl["relay_eth"]), stake + margin))
    for e in [e for e in ev if e["ev"] == "halt"][-1:]:
        if not os.path.exists(hf) and (e.get("t") or 0) > (st.get("t") or 0):          # a halt since the last start, its file removed
            out.append("BASE V2 halt at %s UTC: %s (the file is gone: the engine may still hold the halt until a restart)" % (hms(e["t"]), str(e.get("reason"))[:150]))
    al = [e for e in ev if e["ev"] == "alarm" and now - (e.get("t") or 0) < 900]           # an alarm of the last 15 minutes; older ones are the screen's
    if out or al:
        if al:
            out.append("BASE V2 last alarm %s UTC: %s" % (hms(al[-1]["t"]), str(al[-1].get("what"))[:150]))
        print("\n".join(out))


def main():
    if ALERTS:
        return alerts()
    ev, st, fl = read_logs(HOURS); now = time.time(); active = BW.service_active()
    dry_run = st.get("dry") if st.get("dry") is not None else not BW.live_setting()
    print("=" * W)
    print("%s   service %s   release %s   %s" % ("BASE V2 DRY RUN (nothing is signed or sent)" if dry_run else "BASE V2 LIVE (BASE_V2_DRY_RUN=0: real trades)",
                                             "RUNNING" if active else "STOPPED", st.get("release", "?"),
                                             ("started %s UTC at block %s" % (hm(st["t"]), st.get("head"))) if st else "no start line in " + LOG))
    band = str(cfg(st, "TIER_LABEL", "BASE_V2_TIER_BAND", "1.3,2.3")).replace(",", "-")
    excl = cfg(st, "EXCLUDE_MILLI", "BASE_V2_TIER_EXCLUDE", "1.2")
    excl = ("/".join("%g" % (num(m) / 1000) for m in excl) if isinstance(excl, list) else str(excl).replace(",", "/")) or "none"
    roster_n = st.get("roster_n") if st.get("roster_n") is not None else fl.get("roster_n")
    print("stage settings in force: stake %g ETH (cap %g), %s position(s) at once, %s buys a day, band %s ETH (never %s), hard exit +%s blocks, take profit %s, "
          "daily stop %g ETH, halts at %s losses in a row / %s late buys; roster %s wallets%s"
          % (num(cfg(st, "STAKE_ETH_WEI", "BASE_V2_STAKE_ETH", 0.02, 1e18)), num(cfg(st, "STAKE_CAP_WEI", "BASE_V2_STAKE_CAP_ETH", 0.02, 1e18)),
             cfg(st, "MAX_POSITIONS", "BASE_V2_MAX_POSITIONS", 3), cfg(st, "MAX_PER_DAY", "BASE_V2_MAX_PER_DAY", 20), band, excl,
             cfg(st, "HARD_BLOCK", "BASE_V2_HARD_BLOCK", 180), pct(num(cfg(st, "TP_PPM", "BASE_V2_TAKE_PROFIT", 0.25, 1e6))),
             num(cfg(st, "DAILY_STOP_WEI", "BASE_V2_DAILY_STOP_ETH", 0.15, 1e18)), cfg(st, "LOSS_STREAK_HALT", "BASE_V2_LOSS_STREAK_HALT", 2),
             cfg(st, "LATE_HALT", "BASE_V2_LATE_HALT", 2), roster_n if roster_n is not None else "?", (" (built %s)" % st["roster_built"]) if st.get("roster_built") else ""))
    if fl:
        age = (now - fl["t"]) / 60; quiet = (now - max(fl["t"], st.get("t") or 0)) / 60          # a fresh start has no flow line for its first minute
        up = lambda v: "up" if v else "down"
        msv = lambda v: ("%.0f ms" % num(v)) if v is not None else "-"
        print("feeds: head %s, %s s behind its timestamp; websocket %s, flashblocks %s; since the start: %s creations (%s tradable, %s watched), %s followed, %d open; "
              "today %s fires, P&L %+.4f ETH; last ready %s, last guard %s; the last flow line %.0f min ago%s"
              % (fl.get("head"), fl.get("lag_s"), up(fl.get("ws")), up(fl.get("flash")), fl.get("creations"), fl.get("tradable"), fl.get("watched"), fl.get("followed"),
                 len(fl.get("positions") or []), fl.get("trades_today"), num(fl.get("pnl_today_eth")), msv(fl.get("ready_ms_last")), msv(fl.get("guard_ms_last")), age,
                 "   <== NOT READING (journalctl -u flip-base-v2 -n 30)" if quiet > 3 and active else
                 ("   (restarted %.0f min ago: its first flow line comes a minute in)" % ((now - st["t"]) / 60) if st.get("t", 0) > fl["t"] else "")))
        if fl.get("halted") or fl.get("stopped") or fl.get("tiers_ended"):
            print("   flow says: halted %s, stopped %s, tiers ended today %s" % (fl.get("halted"), fl.get("stopped"), fl.get("tiers_ended") or "none"))
    else:
        print("feeds: no flow line in %s yet (one a minute)" % LOG)
    print("report: the last %g h, to %s UTC" % (HOURS, hm(now)))
    if not ev:
        print("\nno events in the last %g hours: the engine is not running or not logging.  sudo systemctl status flip-base-v2 --no-pager" % HOURS)

    by_pair = {}
    for e in ev:
        p = e.get("pair")
        if not p:
            continue
        d = by_pair.setdefault(p, {"t": e.get("t") or 0})
        if e["ev"] == "trade_done":
            d["live_done" if e.get("live") and not e.get("dry") else "dry_done"] = e
        elif e["ev"] == "skip":
            d.setdefault("skip", e)                                                       # the first skip is the decision
        elif e["ev"] == "outsider_buy":
            d.setdefault("outsiders", []).append(e)
        elif e["ev"] == "guard" and not e.get("self_test"):
            d["guard"] = e
        elif e["ev"] != "guard":
            d[e["ev"]] = e                                                                # a pull line logged pending then confirmed: the last one
    creations = [e for e in ev if e["ev"] == "creation"]; guards = [d["guard"] for d in by_pair.values() if d.get("guard")]
    wf = [e for e in ev if e["ev"] == "would_fire"]; fires = [e for e in ev if e["ev"] == "fire"]; outs = [e for e in ev if e["ev"] == "outsider_buy"]
    pulls = [d["pull"] for d in by_pair.values() if d.get("pull")]
    done = [e for e in ev if e["ev"] == "trade_done"]; dry = [e for e in done if e.get("dry")]; live = [e for e in done if e.get("live") and not e.get("dry")]
    tradable_pairs = {e["pair"] for e in creations if e.get("cls") == "tradable"}
    tiers = {}
    for e in creations:
        t = tiers.setdefault(str(e.get("tier")), {"seen": 0, "tradable": 0, "watched": 0, "skipped": [], "cls": e.get("cls")})
        t["seen"] += 1; t["tradable" if e.get("cls") == "tradable" else "watched"] += 1
        sk = by_pair.get(e.get("pair"), {}).get("skip")
        if sk:
            t["skipped"].append(sk.get("why") or "?")
    print("\nCREATIONS (%g h)      %5s %9s %8s   %s" % (HOURS, "seen", "tradable", "watched", "skipped (the top why)"))
    allrow = {"seen": len(creations), "tradable": sum(t["tradable"] for t in tiers.values()), "watched": sum(t["watched"] for t in tiers.values()),
              "skipped": [w for t in tiers.values() for w in t["skipped"]]}
    for name, t in [("all tiers", allrow)] + sorted(tiers.items(), key=lambda kv: (kv[1]["cls"] != "tradable", -kv[1]["seen"])):
        print("  %-19s %5d %9d %8d   %s" % (name + (" (tolerant)" if t.get("cls") == "tradable" and name != "all tiers" else ""), t["seen"], t["tradable"], t["watched"],
                                            ("%d: %s" % (len(t["skipped"]), count(t["skipped"], lambda w: w, 3))) if t["skipped"] else "0"))
    print("GUARD     %d verdict(s): %s; %s" % (len(guards), count(guards, lambda e: e.get("verdict") or "?"), ms_line([e.get("ms") for e in guards], GUARD_MAX_MS)))
    refused = [d["skip"] for p, d in by_pair.items() if p in tradable_pairs and d.get("skip")]
    print("FIRES     would_fire %d (%s), fire %d (%s); %s; refused on the tolerant tier: %s"
          % (len(wf), count(wf, lambda e: e.get("via") or "?"), len(fires), count(fires, lambda e: e.get("via") or "?"),
             ms_line([e.get("ready_ms") for e in wf + fires], READY_MAX_MS), count(refused, lambda e: e.get("why") or "?")))
    sold = sum(1 for e in outs if e.get("action") == "sell"); skipped_on = sum(1 for e in outs if e.get("action") == "skip")
    since = [num(e.get("since_creation")) for e in pulls if e.get("since_creation") is not None]
    print("OUTSIDERS %d buy(s) logged: %s%s" % (len(outs), count(outs, lambda e: e.get("who") or "?"),
                                                 ("; sold on %d, the pair skipped on %d" % (sold, skipped_on)) if outs else ""))
    print("PULLS     %d%s" % (len(pulls), (": since the creation median +%.0f (min +%.0f, max +%.0f); reactions %d; %s" % (
        statistics.median(since), min(since), max(since), sum(1 for e in pulls if e.get("reaction")),
        count(pulls, lambda e: ("before our " + str(e.get("before"))) if e.get("before") in ("fire", "sell") else "after our sell" if e.get("ours") else "a pair not ours"))) if since else ""))
    print("\nTRADES         count    win    mean ret      net ETH          $ | exits")
    for name, xs in (("dry", dry), ("live", live)):
        rets = [num(e.get("ret")) for e in xs if e.get("ret") is not None]
        print("  %-11s %s  %11s  %9s | %s" % (name, stats(rets), ("%+.6f" % (sum(int(e.get("net_wei") or 0) for e in xs) / 1e18)) if xs else "-",
                                               ("%+.2f" % sum(num(e.get("usd")) for e in xs)) if xs else "-", count(xs, lambda e: e.get("exit") or "?") if xs else "-"))
    if done:
        print("  the last %d (of %d):" % (min(LAST, len(done)), len(done)))
        print("  %-15s %-12s %-8s %-12s %7s %12s %8s  %-22s %s" % ("time (UTC)", "pair", "tier", "exit", "ret", "net ETH", "$", "buy -> sell (blocks)", "pulled at"))
        for e in done[-LAST:]:
            c = e.get("creation"); rel = lambda b: ("+%d" % (b - c)) if isinstance(b, int) and isinstance(c, int) else "-"
            bb, sb = e.get("buy_block"), e.get("sell_block")
            print("  %-15s %-12s %-8s %-12s %7s %12s %8s  %-22s %s%s" % (hms(e["t"]), short(e.get("pair")), e.get("tier"), (e.get("exit") or "?")[:12],
                                                                       pct(num(e.get("ret"))) if e.get("ret") is not None else "?", "%+.6f" % (int(e.get("net_wei") or 0) / 1e18),
                                                                       "%+.2f" % num(e.get("usd")), "%s -> %s%s" % (rel(bb), rel(sb), (" (%d)" % (sb - bb)) if isinstance(sb, int) and isinstance(bb, int) else ""),
                                                                       rel(e.get("pulled_at")), " LIVE" if e.get("live") and not e.get("dry") else ""))
    tol = sorted([(d["t"], p, d) for p, d in by_pair.items() if p in tradable_pairs])
    seen_ok = [d for _, _, d in tol if d.get("creation", {}).get("seen_ms") is not None and num(d["creation"]["seen_ms"]) <= SEEN_MAX_MS]
    guard_ok = [d for _, _, d in tol if d.get("guard") and d["guard"].get("verdict") == "ok" and d["guard"].get("ms") is not None and num(d["guard"]["ms"]) <= GUARD_MAX_MS]
    fired = [d for _, _, d in tol if (d.get("would_fire") or d.get("fire"))]
    ready_ok = [d for d in fired if num((d.get("would_fire") or d.get("fire")).get("ready_ms"), 1e9) <= READY_MAX_MS]
    traded = [d for _, _, d in tol if d.get("dry_done") or d.get("live_done")]
    correct = [d for d in ready_ok if d in guard_ok and d in traded]
    cause = [d for _, _, d in tol if d.get("skip") and str(d["skip"].get("why")).startswith(CAUSE_WHY)]
    watched = [d for p, d in by_pair.items() if d.get("creation") and p not in tradable_pairs]
    right = [d for d in watched if d.get("skip") and d["skip"].get("why") in RIGHT_WHY]
    seen_vals = [num(d["creation"]["seen_ms"]) for _, _, d in tol if d.get("creation", {}).get("seen_ms") is not None]
    drets = [num(d["dry_done"].get("ret")) for d in traded if d.get("dry_done") and d["dry_done"].get("ret") is not None]
    print("\nSTAGE 0 GATE (RUNBOOK 4m step 8: %d correct decisions on the tolerant tier): %d of %d%s" % (GATE_N, len(correct), GATE_N,
          "   <== THREE REACHED: section 9 says the stage ends by your hand" if len(correct) >= GATE_N else " so far"))
    print("  tolerant-tier creations %d: seen within 1 s x%d%s, guard ok under 1 s x%d, would_fire ready under 1,500 ms x%d, trade_done x%d%s; refused for a cause x%d%s"
          % (len(tol), len(seen_ok), (" (seen_ms median %.0f)" % statistics.median(seen_vals)) if seen_vals else " (seen_ms unknown on the logs feed)", len(guard_ok), len(ready_ok), len(traded),
             (" (dry mean %s, pulled %d)" % (pct(sum(drets) / len(drets)), sum(1 for d in traded if d.get("dry_done", {}).get("exit") == "pulled"))) if drets else "",
             len(cause), (" (%s)" % count(cause, lambda d: d["skip"].get("why"))) if cause else ""))
    print("  watched tiers refused with the right why: %d of %d; the probe logged as outsider_buy: %d (%s), the fleet never: %d (%s)"
          % (len(right), len(watched), sum(1 for e in outs if e.get("who") == "probe"), "yes" if any(e.get("who") == "probe" for e in outs) else "none yet",
             sum(1 for e in outs if e.get("who") == "fleet"), "yes" if not any(e.get("who") == "fleet" for e in outs) else "NO: a roster wallet was logged as an outsider"))
    if live or not dry_run:
        first = live[:STAGE1_FIRST]; react = int(num(cfg(st, "REACT_BLOCKS", "BASE_V2_REACT_BLOCKS", 10), 10))
        near = [e for e in live if isinstance(e.get("pulled_at"), int) and isinstance(e.get("buy_block"), int) and 0 <= e["pulled_at"] - e["buy_block"] <= react]
        print("STAGE 1 RULE (live): the first %d: %d trade(s), %d positive; pulls within %d blocks of our buy: %d; halts in the window: %d   (stop at once on a Burn inside %d blocks of our buy on any of the first 3; go on at 3 of 5 positive)"
              % (STAGE1_FIRST, len(first), sum(1 for e in first if num(e.get("ret")) > 0), react, len(near), sum(1 for e in ev if e["ev"] == "halt"), react))

    hf = BV.halt_file()
    print("")
    if os.path.exists(hf):
        try:
            why = open(hf).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        print("HALTED: %s\n  no new buy; an open position is still sold. To resume, once understood: sudo rm %s && sudo systemctl restart flip-base-v2" % (why, hf))
    else:
        print("halt: none (%s)" % hf)
    for e in [e for e in ev if e["ev"] == "halt"][-3:]:
        print("  halt line %s UTC: %s%s" % (hms(e["t"]), str(e.get("reason"))[:150], " (dry: in memory only)" if e.get("dry") else ""))
    stops = today_stops(ev); tl = [e for e in live if time.strftime("%Y-%m-%d", time.gmtime(e.get("t") or 0)) == time.strftime("%Y-%m-%d", time.gmtime())]
    print("today (%s UTC): %d live trade(s), %+.6f ETH ($%+.2f) against the daily stop of -%g ETH%s" % (
        time.strftime("%m-%d", time.gmtime()), len(tl), sum(int(e.get("net_wei") or 0) for e in tl) / 1e18, sum(num(e.get("usd")) for e in tl),
        num(cfg(st, "DAILY_STOP_WEI", "BASE_V2_DAILY_STOP_ETH", 0.15, 1e18), 0.15),
        ("   <== STOPPED FOR THE DAY (%s)" % str([e for e in stops if e.get("what") == "day"][-1].get("reason"))[:100]) if any(e.get("what") == "day" for e in stops) else ""))
    tier_stops = [e for e in stops if e.get("what") == "tier"]
    print("tier stops today: %s" % ("; ".join("%s at %s UTC: %s" % (e.get("tier"), hms(e["t"]), str(e.get("reason"))[:100]) for e in tier_stops) if tier_stops else "none"))
    pos, age = position_state()
    print("open positions: %s" % (("%d (%s)%s" % (len(pos), "; ".join(p[:120] for p in pos), "   <== open %.0f s" % age if age and age > POSITION_OLD_S else ""))
                                  if pos else "none (%s)" % BV.positions_file()))
    for line in balances(st):
        print(line)
    print("(read from %s)" % BW.host(BW.rpc_urls()[0]))
    al = [e for e in ev if e["ev"] == "alarm"]
    if al:
        print("\nALARMS (%d%s):" % (len(al), ", the last 5" if len(al) > 5 else ""))
        for e in al[-5:]:
            print("  %s %s" % (hms(e["t"]), str(e.get("what"))[:150]))
    else:
        print("\nalarms: none")
    print("=" * W)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:                                                              # | head closed the pipe
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno()); sys.exit(0)
