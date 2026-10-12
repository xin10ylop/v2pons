#!/usr/bin/env python3
"""bnb_results.py: the BNB Chain dry run (src/bnb_engine.py, service flip-bnb) in one screen. The reader's state (the head, the lag, the
price), the launches seen per pool size with what the rule would have done (would-have-traded, the dry results: mean, median, share up,
pulled before the sell, the crowd's buys), the creator's dumps per size, the gate before live money, the last 8 launches with their
decision, and the alarms. Nothing here is money: the engine signs nothing and sends nothing.

    sudo python3 ~/v2pons/deploy/bnb_results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/bnb_results.py 72       # the last 72 hours
"""
import glob, gzip, json, os, statistics, subprocess, sys, time
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
LOG = os.environ.get("BNB_LOG_PATH") or "/var/log/flip/bnb.jsonl"; SERVICE = "flip-bnb"; LAST = 8
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
pct = lambda r: "%+.1f%%" % (100 * r)


def read_logs(hours):
    """the events in the window, and the last start and flow lines whenever they were"""
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out, last = [], {}
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ev") in ("start", "flow") and e.get("t", 0) >= last.get(e["ev"], {}).get("t", 0):
                    last[e["ev"]] = e
                if e.get("t", 0) >= t_lo:
                    out.append(e)
        except (FileNotFoundError, EOFError, OSError):
            pass
    return sorted(out, key=lambda e: e.get("t", 0)), last.get("start", {}), last.get("flow", {})


def size_key(x):
    return "%g" % x if isinstance(x, (int, float)) else "?"


def stats(rets):
    if not rets:
        return "%5s %8s %8s %6s" % (0, "-", "-", "-")
    return "%5d %8s %8s %5.0f%%" % (len(rets), pct(sum(rets) / len(rets)), pct(statistics.median(rets)), 100 * sum(1 for r in rets if r > 0) / len(rets))


def main():
    ev, st, fl = read_logs(HOURS); now = time.time()
    active = subprocess.run(["systemctl", "is-active", "--quiet", SERVICE], stderr=subprocess.DEVNULL).returncode == 0
    print("=" * 100)
    print("BNB DRY RUN (nothing is signed or sent)  service %s   release %s   %s" % ("RUNNING" if active else "STOPPED", st.get("release", "?"),
                                                                                 ("started %s UTC" % hm(st["t"])) if st else "no start line in " + LOG))
    if st:
        print("the rule: $%g at L+%s, sold at L+%s; pools of %s BNB skipped; launcher %s, selector %s; the stake at %s $/BNB (%s at the start)"
              % (st.get("stake_usd", 0), st.get("buy_at"), st.get("sell_at"), ", ".join(size_key(x) for x in st.get("skip_pool_bnb", [])) or "no",
                 str(st.get("launcher", "?"))[:10], st.get("selector"), st.get("bnb_usd"), st.get("bnb_usd_src")))
    if fl:
        age = (now - fl["t"]) / 60
        print("reader: block %s, %s blocks behind the head (heads by %s), %s pools watched, %s open; BNB %s $; the last flow line %.0f min ago%s"
              % (fl.get("done_to"), fl.get("lag_blocks"), fl.get("feed") or "?", fl.get("watching"), fl.get("open"), fl.get("bnb_usd"), age,
                 "   <== NOT READING (journalctl -u %s -n 30)" % SERVICE if age > 3 and active else ""))
    print("report: the last %g h, to %s UTC" % (HOURS, hm(now)))
    if not ev:
        print("\nno events in the last %g hours: the dry run is not running or not logging.  sudo systemctl status %s --no-pager" % (HOURS, SERVICE))
    launches = [e for e in ev if e["ev"] == "launch"]; done = [e for e in ev if e["ev"] == "trade_done" and e.get("dry")]
    fires = [e for e in ev if e["ev"] == "would_fire"]; dumps = [e for e in ev if e["ev"] == "dump"]; skips = [e for e in ev if e["ev"] == "skip"]
    sizes = sorted({e.get("pool_bnb") for e in launches + done + dumps if isinstance(e.get("pool_bnb"), (int, float))})
    print("\nPER POOL SIZE (BNB)   launches skipped would-trade | dry trades   mean   median    up | pulled  crowd>=1  crowd BNB | dumps  p50 at  <+997")
    rows = sizes + ["all"]
    for s in rows:
        pick = (lambda e: True) if s == "all" else (lambda e, s=s: e.get("pool_bnb") == s)
        la = [e for e in launches if pick(e)]; dn = [e for e in done if pick(e)]; du = [e for e in dumps if pick(e)]
        rets = [e["dry_ret"] for e in dn if e.get("dry_ret") is not None]
        crowd = [e for e in dn if not e.get("pulled_before_sell")]
        offs = sorted(e["off"] for e in du)
        print("  %-18s %8d %7d %11d | %s | %6d %8s %10s | %5d %7s %6d" % (
            s if s == "all" else size_key(s), len(la), sum(1 for e in la if e.get("skip")), sum(1 for e in fires if pick(e)), stats(rets),
            sum(1 for e in dn if e.get("pulled_before_sell")), ("%d%%" % (100 * sum(1 for e in crowd if e.get("crowd_buys")) / len(crowd))) if crowd else "-",
            ("%.2f" % (sum(e.get("crowd_bnb") or 0 for e in crowd) / len(crowd))) if crowd else "-", len(offs), ("+%d" % offs[len(offs) // 2]) if offs else "-",
            sum(1 for o in offs if o < 997)))
    print("  (crowd>=1: share of the dry trades not dumped on with a crowd buy in the hold; crowd BNB: their BNB a trade; a launch counts in the window "
          "it was seen, a trade in the window it ended)")
    if skips:
        print("not traded besides the skipped sizes: " + "; ".join("%s x%d" % kv for kv in sorted({s["why"]: sum(1 for x in skips if x["why"] == s["why"]) for s in skips}.items())))
    # the gate before live money (REPORT_BNB section 5): halts on any of these
    gb = (st.get("gate") or {}).get("dump_before", 997); cf = (st.get("gate") or {}).get("crowd_from", 60); n_g = (st.get("gate") or {}).get("probes", 10)
    early = [e for e in dumps if e["off"] < gb]; nocrowd = [e for e in done if not e.get("pulled_before_sell") and not e.get("crowd_gate")]
    first = [e["dry_ret"] for e in done[:n_g]]
    print("\nGATE (would halt the line when live)")
    print("  %-32s %s" % ("a dump before +%d:" % gb, "TRIPPED x%d (the last %s UTC, +%d, pool %s BNB)" % (len(early), hms(early[-1]["t"]), early[-1]["off"], early[-1].get("pool_bnb")) if early else "none"))
    print("  %-32s %s" % ("no crowd buy in +%d..+%s:" % (cf, st.get("sell_at", 260)), "TRIPPED x%d (the last %s UTC, %s)" % (len(nocrowd), hms(nocrowd[-1]["t"]), nocrowd[-1]["pair"][:10]) if nocrowd else "none"))
    print("  %-32s %s" % ("a revert:", "not measurable in a dry run (nothing is sent)"))
    print("  %-32s %s" % ("median of the first %d trades:" % n_g, ("%s%s" % (pct(statistics.median(first)), "   <== NEGATIVE" if statistics.median(first) < 0 else "")) if len(first) >= n_g
                                                   else "%d of %d so far" % (len(first), n_g)))
    # the last launches and what the rule did with each
    by_pair = {}
    for e in ev:
        if e.get("pair") and e["ev"] in ("launch", "would_fire", "trade_done", "skip", "dump"):
            by_pair.setdefault(e["pair"], {})[e["ev"]] = e
    order = sorted(by_pair.values(), key=lambda d: (d.get("launch") or d.get("would_fire") or d.get("trade_done") or d.get("skip") or d.get("dump"))["t"])
    print("\nTHE LAST %d LAUNCHES (of %d in the window)" % (min(LAST, len(order)), len(order)))
    if order:
        print("  %-15s %-12s %6s  %-9s %5s %9s %6s %5s  %s" % ("time (UTC)", "pair", "BNB", "decision", "crowd", "crowd BNB", "first", "strgr", "result"))
    for d in order[-LAST:]:
        x = d.get("launch") or d.get("would_fire") or d.get("trade_done") or d.get("skip") or d.get("dump"); td = d.get("trade_done")
        size = x.get("pool_bnb"); dec = "skip" if (d.get("launch") or {}).get("skip") or d.get("skip") else "buy" if d.get("would_fire") else "-"
        if td:
            res = pct(td["dry_ret"]) + ("   <== DUMPED BEFORE THE SELL (+%s)" % td.get("dump_off") if td.get("pulled_before_sell") else "")
            cells = (td.get("crowd_buys"), "%.4f" % (td.get("crowd_bnb") or 0), ("+%s" % td["first_crowd_off"]) if td.get("first_crowd_off") is not None else "-", td.get("strangers"))
        else:
            res = ((d.get("launch") or {}).get("skip") or (d.get("skip") or {}).get("why") or ("open: sells at %s" % (d["would_fire"]["L"] + st.get("sell_at", 260)) if d.get("would_fire") else "-"))[:60]
            cells = ("-", "-", "-", "-")
        if d.get("dump") and not (td and td.get("pulled_before_sell")):
            res += "  (dumped at +%d)" % d["dump"]["off"]
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
