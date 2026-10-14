#!/usr/bin/env python3
"""base_results.py: the Base line (src/base_engine.py, service flip-base; docs/BASE.md) in one screen, from its log (BASE_LOG_PATH,
/var/log/flip/base.jsonl, and the rotated copies). The feeds' state (the last flow line), the launches seen, armed and skipped (with the
reasons), the adds, the fires (would_fire dry, fire live), the trades dry and live (count, mean, median, share up, exits by kind, pulled,
dollars), the pulls, the dry run's gate before live money (RUNBOOK 4l step 2), the halt (HALTED.base), the day's P&L against
BASE_DAILY_STOP_USD, the open position (base_positions.json), the wallet's and the relay's ETH (BASE_WALLET and BASE_RELAY, read from the
RPC; the key file is never opened), the last 8 launches with what happened to each, and the alarms.

    sudo python3 ~/v2pons/deploy/base_results.py           # the last 24 hours
    sudo python3 ~/v2pons/deploy/base_results.py 72        # the last 72 hours
    sudo python3 ~/v2pons/deploy/base_results.py --alerts  # trouble only (nothing when all is well): the halt, a hung reader, a position held too long, the day's stop, the last alarm
"""
import glob, gzip, json, os, statistics, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_wallet as BW                                                                 # standard library only at import: the system python runs this

ALERTS = sys.argv[1:2] == ["--alerts"]
try:
    HOURS = float(sys.argv[1]) if len(sys.argv) > 1 and not ALERTS else 24
except ValueError:
    sys.exit(__doc__.split("\n\n")[1])
LOG = BW.setting("BASE_LOG_PATH", "/var/log/flip/base.jsonl")
LAST = 8
NOT_READING_S = 180                                                                      # no flow line (one a minute) this long while active: the reader hangs
POSITION_OLD_S = 120                                                                     # a position open this long is past any hold (6 blocks = 12 s)
GATE_TRADES, GATE_MEAN = 3, 0.10                                                         # RUNBOOK 4l step 2: 3 dry trades into the bot's buy, +10% or better
SOLD_INTO_BUY = ("bot", "take_profit")
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
pct = lambda r: "%+.1f%%" % (100 * r)
short = lambda x: (str(x)[:10] + "…") if x else "-"


def halt_file():
    return BW.setting("BASE_HALT_FILE") or os.path.join(os.path.dirname(os.path.abspath(LOG)), "HALTED.base")


def read_logs(hours):
    """the events in the window (oldest first), and the last start and flow lines whenever they were"""
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out, last, seen = [], {}, set()
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(e, dict) or "ev" not in e:
                    continue
                if e["ev"] in ("start", "flow") and (e.get("t") or 0) >= (last.get(e["ev"], {}).get("t") or 0):
                    last[e["ev"]] = e
                k = (e.get("t"), e["ev"], e.get("pool"), e.get("dry"))
                if (e.get("t") or 0) >= t_lo and k not in seen:                          # a rotated copy of the same line counts once
                    seen.add(k); out.append(e)
        except (OSError, EOFError):
            pass
    return sorted(out, key=lambda e: e.get("t") or 0), last.get("start", {}), last.get("flow", {})


def cfg(st, k, d=None):
    """a setting as the start line logged it (its settings, or the line itself), else the env file, else the default"""
    s = st.get("settings") if isinstance(st.get("settings"), dict) else {}
    for key in (k, k.lower(), k[5:].lower() if k.startswith("BASE_") else k):
        for src in (s, st):
            if src.get(key) is not None:
                return src[key]
    return BW.setting(k, d)


def num(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def skip_reason(e):
    """the reason a launch was not armed: `skip` holds it, or `reason` / `why` beside skip true or armed false; None when armed"""
    if e.get("armed") is True and not e.get("skip"):
        return None
    for k in ("skip", "reason", "why"):
        if isinstance(e.get(k), str) and e[k]:
            return e[k]
    return "skipped" if e.get("skip") or e.get("armed") is False else None


def stats(xs):
    if not xs:
        return "%5d %8s %8s %5s" % (0, "-", "-", "-")
    return "%5d %8s %8s %4.0f%%" % (len(xs), pct(sum(xs) / len(xs)), pct(statistics.median(xs)), 100 * sum(1 for r in xs if r > 0) / len(xs))


def balances(st):
    """the wallet's and the relay's ETH, from the RPC (BASE_RPC_URL, else BASE_READ_ALT_URL); only the host is printed"""
    out = []
    for name, k in (("wallet", "BASE_WALLET"), ("relay ", "BASE_RELAY")):
        addr = (BW.setting(k) or cfg(st, k) or "")
        if not addr or not str(addr).startswith("0x"):
            out.append("%s: %s not set" % (name, k)); continue
        try:
            b = int(BW.rpc("eth_getBalance", [addr, "latest"], timeout=8), 16) / 1e18
            out.append("%s %s: %.6f ETH ($%.2f)" % (name, addr, b, b * num(cfg(st, "BASE_ETH_USD", 2570), 2570)))
        except Exception as ex:
            out.append("%s %s: balance not read (%s)" % (name, addr, str(ex)[:80]))
    return out


def position_state():
    """(the open positions' texts, the file's age in seconds) from base_positions.json; ([], None) when there is none"""
    p = BW.positions_file()
    try:
        pos = BW.open_positions(); age = time.time() - os.path.getmtime(p) if os.path.exists(p) else None
    except SystemExit as ex:
        return [str(ex)], None
    return pos, age


def today_live(ev_all):
    day = time.strftime("%Y-%m-%d", time.gmtime())
    done = [e for e in ev_all if e["ev"] == "trade_done" and e.get("live") and not e.get("dry") and time.strftime("%Y-%m-%d", time.gmtime(e.get("t") or 0)) == day]
    return done, sum(num(e.get("usd")) for e in done), [e for e in ev_all if e["ev"] == "stop" and str(e.get("day")) == day]


def alerts():
    ev, st, fl = read_logs(3); now = time.time(); out = []
    hf = halt_file()
    if os.path.exists(hf):
        try:
            why = open(hf).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        out.append("BASE HALTED: %s (no new buy; an open position is still sold; deploy/base_results.py has the rest)" % why)
    seen = max(fl.get("t") or 0, st.get("t") or 0)
    if now - seen > NOT_READING_S and BW.service_active():
        out.append("BASE NOT READING: %s while flip-base is active (journalctl -u flip-base -n 30)"
                   % (("no flow line for %.0f min" % ((now - seen) / 60)) if seen else "no flow line in " + LOG))
    pos, age = position_state()
    if pos and (age is None or age > POSITION_OLD_S):
        out.append("BASE POSITION OPEN %s: %s (a hold is 6 blocks, 12 s; look at the relay on basescan)"
                   % (("for %.0f s since the file's last change" % age) if age is not None else "", "; ".join(p[:120] for p in pos)))
    _, day_usd, stops = today_live(ev)
    if stops:
        out.append("BASE STOPPED FOR THE DAY: $%.2f of losses (BASE_DAILY_STOP_USD); new buys resume at 00:00 UTC" % num(stops[-1].get("losses")))
    for e in [e for e in ev if e["ev"] == "halt"][-1:]:
        if not os.path.exists(hf) and (e.get("t") or 0) > (st.get("t") or 0):          # a halt since the last start, its file removed
            out.append("BASE halt at %s UTC: %s (the file is gone: the engine may still hold the halt until a restart)" % (hms(e["t"]), str(e.get("reason"))[:150]))
    al = [e for e in ev if e["ev"] == "alarm"]
    if out or al:
        if al:
            out.append("BASE last alarm %s UTC: %s" % (hms(al[-1]["t"]), str(al[-1].get("what"))[:150]))
        print("\n".join(out))


def main():
    if ALERTS:
        return alerts()
    ev, st, fl = read_logs(HOURS); now = time.time(); active = BW.service_active()
    dry_run = st.get("dry") if st.get("dry") is not None else not BW.live_setting()
    print("=" * 110)
    print("%s   service %s   release %s   %s" % ("BASE DRY RUN (nothing is signed or sent)" if dry_run else "BASE LIVE (BASE_DRY_RUN=0: real trades)",
                                             "RUNNING" if active else "STOPPED", st.get("release", "?"),
                                             ("started %s UTC at block %s" % (hm(st["t"]), st.get("head"))) if st else "no start line in " + LOG))
    print("the line: fee %s / tick spacing %s, hook flags %s, launch %s (%s B), pools of %s ETH and more; stake %s ETH (cap %s), hold %s blocks, "
          "take profit %s, daily stop $%s" % (cfg(st, "BASE_FEE", 5000), cfg(st, "BASE_TICK_SPACING", 100), cfg(st, "BASE_HOOK_FLAGS", "0x80"),
                                              cfg(st, "BASE_LAUNCH_SELECTOR", "c3e0ff3d"), cfg(st, "BASE_LAUNCH_CALLDATA_LEN", 260), cfg(st, "BASE_MIN_POOL_ETH", 1.0),
                                              cfg(st, "BASE_STAKE_ETH", 0.002), cfg(st, "BASE_STAKE_CAP_ETH", 0.005), cfg(st, "BASE_HOLD_BLOCKS", 6),
                                              pct(num(cfg(st, "BASE_TAKE_PROFIT", 0.01))), cfg(st, "BASE_DAILY_STOP_USD", 10)))
    if fl:
        age = (now - fl["t"]) / 60; quiet = (now - max(fl["t"], st.get("t") or 0)) / 60          # a fresh start has no flow line for its first minute
        print("feeds: head %s, %s s behind its timestamp; websocket %s, flashblocks %s; since the start: %s launches, %s armed, %s trades; "
              "the last flow line %.0f min ago%s" % (fl.get("head"), fl.get("lag_s"), fl.get("ws"), fl.get("flash"), fl.get("launches"), fl.get("armed"),
                                                   fl.get("trades"), age, "   <== NOT READING (journalctl -u flip-base -n 30)" if quiet > 3 and active else
                                                   ("   (restarted %.0f min ago: its first flow line comes a minute in)" % ((now - st["t"]) / 60) if st.get("t", 0) > fl["t"] else "")))
        if fl.get("halted") or fl.get("stopped"):
            print("   flow says: halted %s, stopped %s" % (fl.get("halted"), fl.get("stopped")))
    else:
        print("feeds: no flow line in %s yet (one a minute)" % LOG)
    print("report: the last %g h, to %s UTC" % (HOURS, hm(now)))
    if not ev:
        print("\nno events in the last %g hours: the engine is not running or not logging.  sudo systemctl status flip-base --no-pager" % HOURS)

    launches = [e for e in ev if e["ev"] == "launch"]; skipped = [e for e in launches if skip_reason(e)]
    adds = [e for e in ev if e["ev"] == "add"]; wf = [e for e in ev if e["ev"] == "would_fire"]; fires = [e for e in ev if e["ev"] == "fire"]
    skips = [e for e in ev if e["ev"] == "skip"]; pulls = [e for e in ev if e["ev"] == "pull"]; bots = [e for e in ev if e["ev"] == "bot_buy"]
    done = [e for e in ev if e["ev"] == "trade_done"]; dry = [e for e in done if e.get("dry")]; live = [e for e in done if e.get("live") and not e.get("dry")]

    def count(xs, f):
        c = {}
        for e in xs:
            k = f(e); c[k] = c.get(k, 0) + 1
        return "; ".join("%s x%d" % kv for kv in sorted(c.items(), key=lambda kv: -kv[1])) or "none"
    print("\nLAUNCHES  seen %d, armed %d, skipped %d%s" % (len(launches), len(launches) - len(skipped), len(skipped),
                                                     (": " + count(skipped, skip_reason)) if skipped else ""))
    print("ADDS      %d (%s); the pools' ETH: %s" % (len(adds), count(adds, lambda e: "pending" if e.get("pending") else "confirmed"),
                                                  ", ".join(sorted({"%g" % num(e.get("eth")) for e in adds})) or "-"))
    print("FIRES     would_fire %d (%s), fire %d (%s); not fired: %s" % (len(wf), count(wf, lambda e: e.get("via") or "?"), len(fires),
                                                                      count(fires, lambda e: e.get("via") or "?"), count(skips, lambda e: e.get("reason") or e.get("why") or e.get("skip") or "?")))
    print("BOT BUYS  %d seen (%s)" % (len(bots), count(bots, lambda e: e.get("via") or ("pending" if e.get("pending") else "confirmed"))))
    print("\nTRADES             count     mean   median    up | exits%s | pulled |       $" % (" " * 30))
    for name, xs in (("dry", dry), ("live", live)):
        rets = [num(e.get("ret")) for e in xs if e.get("ret") is not None]
        print("  %-14s %s | %-35s | %6d | %+7.2f" % (name, stats(rets), count(xs, lambda e: e.get("exit") or "?") if xs else "-",
                                                     sum(1 for e in xs if e.get("exit") == "pulled"),
                                                     sum(num(e.get("usd")) for e in xs)))
    if pulls:
        print("PULLS     %d: %s" % (len(pulls), count(pulls, lambda e: "before our " + str(e.get("before")) if e.get("before") in ("fire", "sell") else str(e.get("before") or "?"))))
    into = [num(e.get("ret")) for e in dry if e.get("exit") in SOLD_INTO_BUY and e.get("ret") is not None]
    dl = [e for e in dry if e.get("exit") == "deadline"]
    mean = sum(into) / len(into) if into else None
    print("\nDRY GATE (RUNBOOK 4l step 2: %d dry trades sold into the bot's buy, %s or better)" % (GATE_TRADES, pct(GATE_MEAN)))
    print("  sold into a buy behind ours (exit %s): %d, mean %s%s; deadline exits (the bot did not come): %d; pulled: %d" % (
        " or ".join(SOLD_INTO_BUY), len(into), pct(mean) if mean is not None else "-",
        ("   <== PASSED" if len(into) >= GATE_TRADES and mean >= GATE_MEAN else "   (%d of %d so far)" % (len(into), GATE_TRADES) if len(into) < GATE_TRADES else "   <== UNDER " + pct(GATE_MEAN)),
        len(dl), sum(1 for e in dry if e.get("exit") == "pulled")))

    hf = halt_file()
    print("")
    if os.path.exists(hf):
        try:
            why = open(hf).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        print("HALTED: %s\n  no new buy; an open position is still sold. To resume, once understood: sudo rm %s && sudo systemctl restart flip-base" % (why, hf))
    else:
        print("halt: none (%s)" % hf)
    for e in [e for e in ev if e["ev"] == "halt"][-3:]:
        print("  halt line %s UTC: %s" % (hms(e["t"]), str(e.get("reason"))[:150]))
    tl, day_usd, stops = today_live(ev)
    print("today (%s UTC): %d live trade(s), $%+.2f against the daily stop of -$%g%s" % (time.strftime("%m-%d", time.gmtime()), len(tl), day_usd,
                                                                                    num(cfg(st, "BASE_DAILY_STOP_USD", 10), 10),
                                                                                    "   <== STOPPED FOR THE DAY ($%.2f of losses)" % num(stops[-1].get("losses")) if stops else ""))
    pos, age = position_state()
    print("open position: %s" % (("%d (%s)%s" % (len(pos), "; ".join(p[:120] for p in pos), "   <== open %.0f s" % age if age and age > POSITION_OLD_S else ""))
                                 if pos else "none (%s)" % BW.positions_file()))
    for line in balances(st):
        print(line)
    print("(read from %s)" % BW.host(BW.rpc_urls()[0]))

    by_pool = {}
    for e in ev:
        if e.get("pool") and e["ev"] in ("launch", "add", "would_fire", "fire", "trade_done", "pull", "skip", "bot_buy"):
            d = by_pool.setdefault(e["pool"], {})
            d[("live_done" if e.get("live") and not e.get("dry") else "dry_done") if e["ev"] == "trade_done" else e["ev"]] = e
            d.setdefault("t", e.get("t") or 0)
    order = sorted(by_pool.items(), key=lambda kv: kv[1]["t"])
    print("\nTHE LAST %d LAUNCHES (of %d pools in the window)" % (min(LAST, len(order)), len(order)))
    if order:
        print("  %-15s %-9s %-12s %8s  %-8s  %s" % ("time (UTC)", "block", "pool", "pool ETH", "decision", "result"))
    for pid, d in order[-LAST:]:
        la = d.get("launch") or {}; ad = d.get("add") or {}; why = skip_reason(la) if la else None
        dec = "skip" if why or d.get("skip") else ("fire" if d.get("fire") else "dry fire" if d.get("would_fire") else "armed" if la else "-")
        res = []
        if why:
            res.append(why[:60])
        if d.get("skip") and not why:
            res.append(str(d["skip"].get("reason") or d["skip"].get("why") or d["skip"].get("skip"))[:60])
        for k, name in (("dry_done", "dry"), ("live_done", "LIVE")):
            td = d.get(k)
            if td:
                res.append("%s %s exit %s%s%s" % (name, pct(num(td.get("ret"))) if td.get("ret") is not None else "?", td.get("exit"),
                                                  " ($%+.2f)" % num(td.get("usd")) if k == "live_done" else "",
                                                  " (sold %+d blocks after the buy)" % (td["sell_block"] - td["buy_block"]) if isinstance(td.get("sell_block"), int) and isinstance(td.get("buy_block"), int) else ""))
        if d.get("pull"):
            res.append("pulled at %s (%s)" % (d["pull"].get("block"), d["pull"].get("before")))
        if not res and dec in ("dry fire", "fire"):
            res.append("open")
        print("  %-15s %-9s %-12s %8s  %-8s  %s" % (hms(d["t"]), la.get("block") or ad.get("block") or "-", short(pid),
                                                    ("%.4g" % num(ad.get("eth"))) if ad else "-", dec, "; ".join(res) or "-"))
    al = [e for e in ev if e["ev"] == "alarm"]
    if al:
        print("\nALARMS (%d%s):" % (len(al), ", the last 5" if len(al) > 5 else ""))
        for e in al[-5:]:
            print("  %s %s" % (hms(e["t"]), str(e.get("what"))[:150]))
    else:
        print("\nalarms: none")
    print("=" * 110)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:                                                              # | head closed the pipe
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno()); sys.exit(0)
