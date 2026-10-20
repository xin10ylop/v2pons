#!/usr/bin/env python3
"""bnb_results.py: the BNB Chain dry run (src/bnb_engine.py, service flip-bnb) in one screen. The reader's state (the head, the lag, the
price), the launches seen per pool size with what the rule would have done (would-have-traded, the dry results: mean, median, share up,
pulled before the sell, the crowd's buys), the creator's dumps per size, the gate before live money, the last 8 launches with their
decision, and the alarms. A trade with a missed log or a gap (not "clean") is left out of every statistic and of the gate, and counted.
With BNB_LIVE=1 (src/bnb_live.py, RUNBOOK 4k) it adds LIVE vs CONTROL: the live trades settled from their receipts, the same pools at
the dry price, and the other launches left dry; the halt (HALTED.bnb), the open positions (bnb_positions.json), the day against its stop,
and the wallet's balance (BNB_WALLET, read from the RPC; the key file is never opened). Dry, nothing here is money.

    sudo python3 ~/v2pons/deploy/bnb_results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/bnb_results.py 72       # the last 72 hours
    sudo python3 ~/v2pons/deploy/bnb_results.py --alerts # live trouble only: the halt, a stuck or overdue position, a hung reader, the last alarm (health.sh)
"""
import glob, gzip, json, os, statistics, subprocess, sys, time, urllib.parse, urllib.request
ALERTS = sys.argv[1:2] == ["--alerts"]                                         # health.sh: only what needs the owner now (nothing when all is well)
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 and not ALERTS else 24
LOG = os.environ.get("BNB_LOG_PATH") or "/var/log/flip/bnb.jsonl"; SERVICE = "flip-bnb"; LAST = 8
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
pct = lambda r: "%+.1f%%" % (100 * r)
ENV_FILE = os.environ.get("BNB_ENV_FILE") or "/etc/flip/bnb.env"
BLOCK_S = 0.45                                                                 # BNB Chain's block time: the head now from the last flow line's, by the clock
NOT_READING_S = 180                                                            # no flow line (one a minute) this long while the service is active: the reader hangs


def service_active():
    """systemctl's word on flip-bnb (False where there is no systemctl)"""
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", SERVICE], stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def setting(k, d=None):
    """a setting as the engine sees it: the environment, else the env file's last line for it (root: sudo), else the default"""
    if os.environ.get(k):
        return os.environ[k].split(" #", 1)[0].strip()
    v = None
    try:
        for line in open(ENV_FILE):
            if line.startswith(k + "="):
                v = line.split("=", 1)[1].split(" #", 1)[0].strip() or None
    except OSError:
        pass
    return v if v is not None else d


def own_file(path):
    """the BNB line's own file in the shared /var/log/flip (src/bnb_live.py's rule): HALTED.bnb, or a name that starts with bnb"""
    b = os.path.basename(path)
    return b == "HALTED.bnb" or b.startswith("bnb")


def wallet_balance(wallet, url):
    """the wallet's BNB by eth_getBalance (only the URL's host is ever printed: the URL may hold a provider's key)"""
    try:
        req = urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [wallet, "latest"]}).encode(),
                                     {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
        return int(json.load(urllib.request.urlopen(req, timeout=8))["result"], 16) / 1e18, None
    except Exception as e:
        return None, type(e).__name__


def live_section(ev, st, fl, n_g):
    """LIVE vs CONTROL, the halt, the open positions and the day, the wallet"""
    live = [e for e in ev if e["ev"] == "trade_done" and e.get("live")]; dry = [e for e in ev if e["ev"] == "trade_done" and e.get("dry")]
    usd = fl.get("bnb_usd") or st.get("bnb_usd") or 0
    sizes = ", ".join("%g" % x for x in st.get("live_pool_bnb") or []) or "every traded"
    print("\nLIVE vs CONTROL (every %s-th launch of the %s BNB pools live at $%g, the others of those sizes dry; the trades that ended in the window)"
          % (st.get("probe_every", "?"), sizes, st.get("stake_usd", 0)))
    print("  %-38s %5s %8s %8s %6s | %9s" % ("", "count", "mean", "median", "up", "$"))

    def row(name, rets, dollars, note=""):
        print("  %-38s %s | %9s%s" % (name, stats(rets), ("%+.2f" % dollars) if rets else "-", note))
    traded = [e for e in live if not e.get("reverted") and e.get("pnl_pct") is not None]
    nrev = sum(1 for e in live if e.get("reverted"))
    row("LIVE (the receipts, after gas)", [e["pnl_pct"] for e in traded], sum(e.get("pnl_usd") or 0 for e in live),
        "   ($ includes %d reverted buy(s))" % nrev if nrev else "")
    same = [e for e in traded if e.get("dry_ret") is not None]
    row("LIVE's pools at the dry price", [e["dry_ret"] for e in same], sum(e["dry_ret"] * (e.get("stake_wei") or 0) / 1e18 * (e.get("bnb_usd") or usd) for e in same))
    ctl = [e for e in dry if e.get("role") == "control" and clean(e)]
    row("CONTROL (the other launches, dry)", [e["dry_ret"] for e in ctl], sum(e["dry_ret"] * (e.get("stake_wei") or 0) / 1e18 * usd for e in ctl))
    gap = [e["gross_pct"] - e["dry_ret_gross"] for e in same if e.get("gross_pct") is not None and e.get("dry_ret_gross") is not None]
    if gap:
        print("  live gross minus its dry price's gross: median %s (the buy lands a few blocks after L+%s, the sale a few after L+%s)"
              % (pct(statistics.median(gap)), st.get("buy_at"), st.get("sell_at")))
    skips = [e for e in ev if e["ev"] == "live_skip"]
    if skips:
        kinds = {}
        for e in skips:
            kinds.setdefault(str(e.get("role")), []).append(e.get("why") or "")
        print("  live slots not traded: " + "; ".join("%s %d (the last: %s)" % (k, len(v), v[-1][:70]) for k, v in sorted(kinds.items())))
    checked = [e for e in ev if e["ev"] == "live_check"]; refused = [e for e in checked if not e.get("ok")]
    if checked:
        print("  pre-buy checks: %d, refused %d%s" % (len(checked), len(refused), (" (the last: %s)" % str(refused[-1].get("why"))[:80]) if refused else ""))
    halt_file = setting("BNB_HALT_FILE") or os.path.join(os.path.dirname(os.path.abspath(LOG)), "HALTED.bnb")
    pos_file = setting("BNB_POSITIONS_FILE") or os.path.join(os.path.dirname(os.path.abspath(LOG)), "bnb_positions.json")
    if not own_file(halt_file):                                                # never tell the owner to remove flip-engine's halt (/var/log/flip/HALTED)
        print("BNB_HALT_FILE %s is not the line's own file (HALTED.bnb or a name starting with bnb): the live engine refuses to start with it; "
              "fix /etc/flip/bnb.env" % halt_file)
    elif os.path.exists(halt_file):
        try:
            why = open(halt_file).read().strip()[:150] or "(empty file)"
        except OSError:
            why = "(not readable: sudo)"
        print("HALTED: %s\n  no new live buy; open positions are still sold. To resume, once understood: sudo rm %s && sudo systemctl restart %s"
              % (why, halt_file, SERVICE))
    elif halt_in_positions(read_json(pos_file), halt_file):
        print("HALTED: %s\n  no new live buy; open positions are still sold" % halt_in_positions(read_json(pos_file), halt_file))
    else:
        print("halt: none (%s)" % halt_file)
    try:
        d = json.load(open(pos_file))
        pos = d.get("positions") or {}; g = d.get("gate_rets") or []
        opened = ", ".join("%s %s%s" % (k[:10], x.get("state"), (", selling: " + x["sell_due"]["why"]) if x.get("sell_due") else "") for k, x in pos.items())
        print("open live positions: %d%s; today (%s UTC) $%+.2f against the daily stop of -$%g; the gate's median: %s"
              % (len(pos), (" (%s)" % opened) if pos else "", d.get("day"), d.get("pnl_today_usd") or 0, float(st.get("daily_stop_usd") or 10),
                 ("%s over the first %d live trades%s" % (pct(statistics.median(g)), len(g), "   <== NEGATIVE" if statistics.median(g) < 0 else ""))
                 if len(g) >= n_g else "%d of %d live trades so far" % (len(g), n_g)))
    except FileNotFoundError:
        print("open live positions: none (no %s yet)" % pos_file)
    except Exception as e:
        print("open live positions: %s not read (%s)" % (pos_file, type(e).__name__))
    wallet = setting("BNB_WALLET") or st.get("wallet")
    if wallet:
        url = setting("BNB_RPC_URL", "https://bsc-rpc.publicnode.com"); bal, err = wallet_balance(wallet, url)
        print("wallet %s: %s (read from %s)" % (wallet, ("%.6f BNB, $%.2f" % (bal, bal * usd)) if bal is not None else "balance not read (%s)" % err,
                                                 urllib.parse.urlparse(url).hostname))


def read_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def read_logs(hours):
    """the events in the window, the last start and flow lines whenever they were, and every dry trade in all the logs kept"""
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out, last, done = [], {}, {}
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ev") in ("start", "flow") and e.get("t", 0) >= last.get(e["ev"], {}).get("t", 0):
                    last[e["ev"]] = e
                if e.get("ev") == "trade_done" and e.get("dry"):
                    done[(e.get("t"), e.get("pair"))] = e                           # a rotated copy of the same line counts once
                if e.get("t", 0) >= t_lo:
                    out.append(e)
        except (FileNotFoundError, EOFError, OSError):
            pass
    return sorted(out, key=lambda e: e.get("t", 0)), last.get("start", {}), last.get("flow", {}), sorted(done.values(), key=lambda e: e.get("t", 0))


def clean(e):
    """a dry trade with no missed log and no gap (older lines have no "clean" field: the same rule from breaks, gaps and dry_ret)"""
    return e.get("dry_ret") is not None and not e.get("breaks") and not e.get("gaps")


def size_key(x):
    return "%g" % x if isinstance(x, (int, float)) else "?"


def stats(rets):
    if not rets:
        return "%5s %8s %8s %6s" % (0, "-", "-", "-")
    return "%5d %8s %8s %5.0f%%" % (len(rets), pct(sum(rets) / len(rets)), pct(statistics.median(rets)), 100 * sum(1 for r in rets if r > 0) / len(rets))


def halt_in_positions(d, halt_file):
    """the engine's halt as its positions file holds it, when HALTED.bnb does not: never written (the engine keeps trying), or removed by
    the owner while the engine still runs halted (it reads the file only at its start)"""
    if not d.get("halted") or os.path.exists(halt_file):
        return None
    return "%s (%s)" % (str(d["halted"])[:150], "only in the positions file: HALTED.bnb could not be written" if d.get("halt_written") is False
                        else "HALTED.bnb was removed but the engine still holds the halt: restart flip-bnb to resume")


def head_by_clock(fl, x, buy_at, now):
    """the chain's head now, by the clock: the last flow line's head plus a block for every BLOCK_S since (a reader that stalls stops
    writing them), and no less than L+BNB_BUY_AT plus the blocks since the position's buy was sent; None when neither is known"""
    est = []
    if fl.get("t") and (fl.get("head") or fl.get("done_to")):
        est.append((fl.get("head") or fl["done_to"]) + int((now - fl["t"]) / BLOCK_S))
    buy = next((t for t in x.get("txs") or [] if t.get("kind") == "buy" and t.get("sent_at")), None)
    if buy and x.get("L"):
        est.append(x["L"] + buy_at + int((now - buy["sent_at"]) / BLOCK_S))
    return max(est) if est else None


def alerts():
    """the line's trouble in a few lines for health.sh (nothing when all is well): the halt (its file, or the positions file when the file
    is not there), a reader that wrote no flow line for 3 minutes while the service is active, a live position stuck, past its sale by 100
    blocks by the clock (not by the last flow line's head: a reader that stalls stops moving it) or with a sale pending over a minute, and
    the last alarm of the last 3 hours (the gate's dry alarms aside)"""
    ev, st, fl, _ = read_logs(3); now = time.time(); out = []
    halt_file = setting("BNB_HALT_FILE") or os.path.join(os.path.dirname(os.path.abspath(LOG)), "HALTED.bnb")
    pos_file = setting("BNB_POSITIONS_FILE") or os.path.join(os.path.dirname(os.path.abspath(LOG)), "bnb_positions.json")
    if own_file(halt_file) and os.path.exists(halt_file):
        try:
            why = open(halt_file).read().strip()[:150]
        except OSError:
            why = "(not readable: sudo)"
        out.append("BNB HALTED: %s (no new live buy; open positions still sold; deploy/bnb_results.py has the rest)" % why)
    try:
        d = json.load(open(pos_file)); pos = d.get("positions") or {}
    except FileNotFoundError:
        d, pos = {}, {}
    except Exception as e:
        d, pos = {}, {}; out.append("BNB positions file %s not read (%s)" % (pos_file, type(e).__name__))
    held = halt_in_positions(d, halt_file) if own_file(halt_file) else None
    if held:
        out.append("BNB HALTED: %s (no new live buy; open positions still sold)" % held)
    seen = max(fl.get("t") or 0, st.get("t") or 0)                             # the last flow line, or the start when none came since
    if now - seen > NOT_READING_S and service_active():
        out.append("BNB NOT READING: %s while flip-bnb is active (the reader hangs; sales go by the chain's head: journalctl -u %s -n 30)"
                   % (("no flow line for %.0f min" % ((now - seen) / 60)) if seen else "no flow line in " + LOG, SERVICE))
    sell_at, buy_at = st.get("sell_at", 260), st.get("buy_at", 50)
    for k, x in pos.items():
        last = (x.get("txs") or [{}])[-1]; due = x.get("sell_due") or {}; head = head_by_clock(fl, x, buy_at, now)
        if x.get("state") == "stuck":
            out.append("BNB STUCK %s: the tokens stay in the wallet (%s); a restart of flip-bnb tries to sell them again" % (k[:12], due.get("why") or "no sale"))
        elif head and x.get("L") and head - x["L"] > sell_at + 100:
            out.append("BNB SALE OVERDUE %s: %s at about L+%d by the clock (sold at L+%s)" % (k[:12], x.get("state"), head - x["L"], sell_at))
        elif x.get("state") == "sell_sent" and last.get("sent_at") and now - last["sent_at"] > 60:
            out.append("BNB SELL PENDING %s: %.0f s, %s" % (k[:12], now - last["sent_at"], last.get("hash")))
    al = [e for e in ev if e["ev"] == "alarm" and not str(e.get("what", "")).startswith("gate:")]
    if out or al:
        if al:
            out.append("BNB last alarm %s UTC: %s" % (hms(al[-1]["t"]), str(al[-1].get("what"))[:150]))
        print("\n".join(out))


def main():
    if ALERTS:
        return alerts()
    ev, st, fl, all_done = read_logs(HOURS); now = time.time()
    active = service_active()
    print("=" * 100)
    live = bool(st.get("live")) or any(e.get("live") for e in ev if e["ev"] == "trade_done")
    print("%s  service %s   release %s   %s" % ("BNB LIVE PROBE (BNB_LIVE=1: real trades)" if live else "BNB DRY RUN (nothing is signed or sent)",
                                            "RUNNING" if active else "STOPPED", st.get("release", "?"), ("started %s UTC" % hm(st["t"])) if st else "no start line in " + LOG))
    if st:
        print("the rule: $%g at L+%s, sold at L+%s; pools of %s BNB skipped; launcher %s, selector %s; the stake at %s $/BNB (%s at the start)"
              % (st.get("stake_usd", 0), st.get("buy_at"), st.get("sell_at"), ", ".join(size_key(x) for x in st.get("skip_pool_bnb", [])) or "no",
                 str(st.get("launcher", "?"))[:10], st.get("selector"), st.get("bnb_usd"), st.get("bnb_usd_src")))
    if fl:
        age = (now - fl["t"]) / 60
        print("reader: block %s, %s blocks behind the head (heads by %s), %s pools watched, %s open; BNB %s $; the last flow line %.0f min ago%s"
              % (fl.get("done_to"), fl.get("lag_blocks"), fl.get("feed") or "?", fl.get("watching"), fl.get("open"), fl.get("bnb_usd"), age,
                 "   <== NOT READING (journalctl -u %s -n 30)" % SERVICE if age > 3 and active else ""))
        if isinstance(fl.get("blocks"), int) and fl["blocks"] < 60:
            print("   <== SLOW: %d blocks read in the last flow line's minute (about 133 a minute expected)" % fl["blocks"])
    print("report: the last %g h, to %s UTC" % (HOURS, hm(now)))
    if not ev:
        print("\nno events in the last %g hours: the dry run is not running or not logging.  sudo systemctl status %s --no-pager" % (HOURS, SERVICE))
    launches = [e for e in ev if e["ev"] == "launch"]; done_all = [e for e in ev if e["ev"] == "trade_done" and e.get("dry")]
    done = [e for e in done_all if clean(e)]; left_out = [e for e in done_all if not clean(e)]
    gb = (st.get("gate") or {}).get("dump_before", 997); cf = (st.get("gate") or {}).get("crowd_from", 60); n_g = (st.get("gate") or {}).get("probes", 10)
    fires = [e for e in ev if e["ev"] == "would_fire"]; dumps = [e for e in ev if e["ev"] == "dump"]; skips = [e for e in ev if e["ev"] == "skip"]
    sizes = sorted({e.get("pool_bnb") for e in launches + done + dumps if isinstance(e.get("pool_bnb"), (int, float))})
    print("\nPER POOL SIZE (BNB)   launches skipped would-trade | dry trades   mean   median    up | pulled  crowd>=1  crowd BNB | dumps  p50 at  <+%d" % gb)
    rows = sizes + ["all"]
    for s in rows:
        pick = (lambda e: True) if s == "all" else (lambda e, s=s: e.get("pool_bnb") == s)
        la = [e for e in launches if pick(e)]; dn = [e for e in done if pick(e)]; du = [e for e in dumps if pick(e)]
        rets = [e["dry_ret"] for e in dn if e.get("dry_ret") is not None]
        crowd = [e for e in dn if not e.get("pulled_before_sell")]
        offs = sorted(e["off"] for e in du)
        print("  %-18s %8d %7d %11d | %s | %6d %8s %10s | %5d %7s %6d" % (
            s if s == "all" else size_key(s), len(la), sum(1 for e in la if e.get("skip")), sum(1 for e in fires if pick(e)), stats(rets),
            sum(1 for e in dn if e.get("pulled_before_sell")), ("%.0f%%" % (100 * sum(1 for e in crowd if e.get("crowd_buys")) / len(crowd))) if crowd else "-",
            ("%.2f" % (sum(e.get("crowd_bnb") or 0 for e in crowd) / len(crowd))) if crowd else "-", len(offs), ("+%d" % offs[len(offs) // 2]) if offs else "-",
            sum(1 for o in offs if o < gb)))
    print("  (crowd>=1: share of the dry trades not dumped on with a crowd buy in the hold; crowd BNB: their BNB a trade; a launch counts in the window "
          "it was seen, a trade in the window it ended)")
    if left_out:
        print("LEFT OUT of every number above and of the gate: %d dry trade(s) with a missed log or a gap (breaks/gaps in the line; the last %s UTC, %s)"
              % (len(left_out), hms(left_out[-1]["t"]), left_out[-1].get("why")))
    if skips:
        print("not traded besides the skipped sizes: " + "; ".join("%s x%d" % kv for kv in sorted({s["why"]: sum(1 for x in skips if x["why"] == s["why"]) for s in skips}.items())))
    # the gate before live money (REPORT_BNB section 5): halts on any of these; the median over the first trades since the engine's start
    early = [e for e in dumps if e["off"] < gb]; nocrowd = [e for e in done if not e.get("pulled_before_sell") and not e.get("crowd_gate")]
    first = [e["dry_ret"] for e in all_done if clean(e) and e.get("t", 0) >= st.get("t", 0)][:n_g]
    all_note = lambda xs, n: "   (all pools, dry: x%d)" % n if n != len(xs) else ""
    if live:                                                                   # what the live line halts on: a dump on a pool of the line (the skipped sizes
        skipped = {e["pair"] for e in launches if e.get("skip")}               # aside), no crowd on a pool it traded; the dry count of all pools beside
        skip_sizes = st.get("skip_pool_bnb") or []
        early_all, nocrowd_all = len(early), len(nocrowd)
        early = [e for e in early if e.get("pair") not in skipped and not any(abs((e.get("pool_bnb") or 0) - x) < 0.005 for x in skip_sizes)]
        traded = {e["pair"] for e in ev if (e["ev"] == "trade_done" and e.get("live")) or (e["ev"] == "live_send" and e.get("kind") == "buy")}
        nocrowd = [e for e in nocrowd if e["pair"] in traded]
    print("\nGATE (%s)" % ("halts the live line" if live else "would halt the line when live"))
    print("  %-42s %s%s" % ("a dump before +%d:" % gb, "TRIPPED x%d (the last %s UTC, +%d, pool %s BNB)" % (len(early), hms(early[-1]["t"]), early[-1]["off"], early[-1].get("pool_bnb")) if early else "none",
                            all_note(early, early_all) if live else ""))
    print("  %-42s %s%s" % ("no crowd buy in +%d..+%s:" % (cf, st.get("sell_at", 260)), "TRIPPED x%d (the last %s UTC, %s)" % (len(nocrowd), hms(nocrowd[-1]["t"]), nocrowd[-1]["pair"][:10]) if nocrowd else "none",
                            all_note(nocrowd, nocrowd_all) if live else ""))
    reverts = [e for e in ev if e["ev"] == "live_receipt" and not e.get("status")]
    print("  %-42s %s" % ("a revert:", ("TRIPPED x%d (the last %s UTC, a %s)" % (len(reverts), hms(reverts[-1]["t"]), reverts[-1].get("kind")) if reverts else "none")
                          if live else "not measurable in a dry run (nothing is sent)"))
    print("  %-42s %s" % ("median of the first %d trades:" % n_g if not st else "median of the first %d since %s:" % (n_g, hm(st["t"])), ("%s%s" % (pct(statistics.median(first)), "   <== NEGATIVE" if statistics.median(first) < 0 else "")) if len(first) >= n_g
                                                   else "%d of %d so far" % (len(first), n_g)))
    if live:
        live_section(ev, st, fl, n_g)
    # the last launches and what the rule did with each
    by_pair = {}
    for e in ev:
        if e.get("pair") and e["ev"] in ("launch", "would_fire", "trade_done", "skip", "dump"):
            by_pair.setdefault(e["pair"], {})["live_done" if e.get("live") else e["ev"]] = e
    order = sorted(by_pair.values(), key=lambda d: (d.get("launch") or d.get("would_fire") or d.get("trade_done") or d.get("skip") or d.get("dump") or d.get("live_done"))["t"])
    print("\nTHE LAST %d LAUNCHES (of %d in the window)" % (min(LAST, len(order)), len(order)))
    if order:
        print("  %-15s %-12s %6s  %-9s %5s %9s %6s %5s  %s" % ("time (UTC)", "pair", "BNB", "decision", "crowd", "crowd BNB", "first", "strgr", "result"))
    for d in order[-LAST:]:
        x = d.get("launch") or d.get("would_fire") or d.get("trade_done") or d.get("skip") or d.get("dump") or d.get("live_done"); td = d.get("trade_done")
        size = x.get("pool_bnb"); dec = "skip" if (d.get("launch") or {}).get("skip") or d.get("skip") else "buy" if d.get("would_fire") else "-"
        if (d.get("trade_done") or {}).get("role"):
            dec += "/" + d["trade_done"]["role"][:4]
        if td:
            res = (pct(td["dry_ret"]) if td.get("dry_ret") is not None else "no result") + ("   <== DUMPED BEFORE THE SELL (+%s)" % td.get("dump_off") if td.get("pulled_before_sell") else "") \
                + ("   (left out: a missed log or a gap)" if not clean(td) else "")
            cells = (td.get("crowd_buys"), "%.4f" % (td.get("crowd_bnb") or 0), ("+%s" % td["first_crowd_off"]) if td.get("first_crowd_off") is not None else "-", td.get("strangers"))
        else:
            res = ((d.get("launch") or {}).get("skip") or (d.get("skip") or {}).get("why") or ("open: sells at %s" % (d["would_fire"]["L"] + st.get("sell_at", 260)) if d.get("would_fire") else "-"))[:60]
            cells = ("-", "-", "-", "-")
        if d.get("dump") and not (td and td.get("pulled_before_sell")):
            res += "  (dumped at +%d)" % d["dump"]["off"]
        if d.get("live_done"):
            ld = d["live_done"]
            res += "   LIVE %s $%+.2f%s" % (pct(ld["pnl_pct"]) if ld.get("pnl_pct") is not None else "-", ld.get("pnl_usd") or 0, " REVERTED " + ld["reverted"] if ld.get("reverted") else "")
        print("  %-15s %-12s %6s  %-9s %5s %9s %6s %5s  %s" % (hms(x["t"]), x["pair"][:12], size_key(size), dec, *cells, res))
    al = [e for e in ev if e["ev"] == "alarm"]
    if al:
        print("\nALARMS (%d%s; 'gate:' ones are the gate's):" % (len(al), ", the last 5" if len(al) > 5 else ""))
        for e in al[-5:]:
            print("  %s %s" % (hms(e["t"]), str(e.get("what"))[:150]))
    else:
        print("\nalarms: none")
    print("=" * 100)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:                                                    # | head closed the pipe: the rest is not wanted
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno()); sys.exit(0)
