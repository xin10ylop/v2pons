#!/usr/bin/env python3
"""results.py: the flip engine's results in one screen. The engine's state (live or dry run, halted or not), each front line (a launch
family: v2.433, c1, v3.0, v3crowd, ...) with its stake and its live result over the last hour, today, the report's window and every log
kept, the last live trades, each line's detail, the launches seen per line, the dry lines' decisions, the alarms, and the money in the
wallet and the relay. Follow is not shown.

    sudo python3 ~/v2pons/deploy/results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/results.py 72       # the last 72 hours
"""
import glob, gzip, json, os, re, subprocess, sys, time, urllib.request
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
LOG = "/var/log/flip/engine.jsonl"; ENV = "/etc/flip/engine.env"; HALT = "/var/log/flip/HALTED"
LAST_TRADES = 8                                                                # live trades listed one by one (every filled one counts in the table)
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
usd = lambda u: "%s$%.2f" % ("+" if u >= 0 else "-", abs(u))
pct = lambda r: "%+.1f%%" % (100 * r)
n_of = lambda n, w: "%d %s%s" % (n, w, "" if n == 1 else "s")


def read_logs(hours):
    """the events in the window, every live trade's result in all the logs, and the engine's last start and status lines whenever
    they were (a start before the window still says how it runs)"""
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out = []; last = {}; done = {}
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ev") in ("start", "flow") and e.get("t", 0) >= last.get(e["ev"], {}).get("t", 0):
                    last[e["ev"]] = e
                if e.get("ev") == "trade_done" and not e.get("dry"):
                    done[(e.get("t"), e.get("nonce"))] = e                       # a rotated copy of the same line counts once
                if e.get("t", 0) >= t_lo:
                    out.append(e)
        except (FileNotFoundError, EOFError, OSError):
            pass
    return sorted(out, key=lambda e: e.get("t", 0)), last.get("start", {}), last.get("flow", {}), sorted(done.values(), key=lambda e: e.get("t", 0))


def env():
    d = {}
    try:
        for line in open(ENV):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); d[k.strip()] = v.split(" #", 1)[0].strip()
    except Exception:
        pass
    return d


def num(x, default):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def balance(rpc, addr):
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(rpc, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [addr, "latest"]}).encode(),
                                                                    {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}), timeout=5))
        return int(r["result"], 16) / 1e18
    except Exception:
        return None


def families(st, e, now):
    """the front lines as the engine's last start line lists them (release 0.9's families); before families existed, the one FRONT_* line.
    Each: name, mode (LIVE: its trades are sent; dry; off), its stake in ETH (the auto stake's ceiling when the stake is automatic), the
    auto stake now (from the engine's last status line of this run, if any), and the base line's name (the FRONT_* line: trades logged
    before families existed are its)"""
    dry_all = st.get("dry_run", e.get("DRY_RUN", "1") != "0") if st else e.get("DRY_RUN", "1") != "0"
    front_on = (st.get("front", e.get("FRONT", "0") != "0") if st else e.get("FRONT", "0") != "0") and not now.get("front_halted")
    front_dry = st.get("front_dry_run", e.get("FRONT_DRY_RUN", "1") != "0") if st else e.get("FRONT_DRY_RUN", "1") != "0"
    fams = st.get("front_families")
    if fams is None:                                                           # an older start line (or none): the FRONT_* line alone
        fams = [{"name": e.get("FRONT_FAMILY_NAME", "v2.433"), "stake_eth": num(st.get("front_stake_eth", e.get("FRONT_STAKE_ETH")), 0), "dry_run": False, "trigger": None}]
    auto_on = bool(st.get("front_auto_stake", e.get("FRONT_AUTO_STAKE", "0") != "0")); auto = now.get("auto_stake_eth") or {}
    out = []
    for f in fams:
        if not front_on:
            mode = "off"
        elif dry_all or front_dry or f.get("dry_run") or (f.get("dex") == "v3" and not f.get("live")):   # a V3 family is dry unless the start line says it is live (RELAY_V3)
            mode = "dry"
        else:
            mode = "LIVE"
        stake = f.get("live_stake_eth", f.get("stake_eth")) if mode == "LIVE" else f.get("stake_eth")   # a live V3 family's stake under V3_STAKE_CAP_ETH
        out.append({"name": f["name"], "mode": mode, "stake_eth": num(stake, 0), "auto": auto_on and not f.get("trigger"), "auto_eth": auto.get(f["name"]),
                    "dex": f.get("dex", "v4"), "trigger": f.get("trigger"), "value_eth": f.get("value_eth")})
    base_wei = num(st.get("front_value_wei"), None)
    base = next((f["name"] for f in out if base_wei and f.get("value_eth") is not None and abs(f["value_eth"] * 1e18 - base_wei) < 1e9), None) or e.get("FRONT_FAMILY_NAME", "v2.433")
    return out, base


def pull_summary(ds):
    """the operator's reaction to the line's trades: its pull, in blocks after our sell landed, in four bands; the pulls before our sell"""
    bands = {"0-1": 0, "2-3": 0, "4-9": 0, "10+": 0}; first = later = failed = 0
    for d in ds:
        sold, pull = d.get("sell_after_buy_blocks"), d.get("pull_after_buy_blocks")
        if d.get("pulled_before_sell") or (pull is not None and sold is not None and pull < sold):
            first += 1
        elif pull is not None and sold is not None:
            g = pull - sold; bands["0-1" if g <= 1 else "2-3" if g <= 3 else "4-9" if g <= 9 else "10+"] += 1
        elif d.get("pull_check"):
            failed += 1
        elif "pull_after_buy_blocks" in d:
            later += 1
    parts = ["%s blocks x%d" % (k, v) for k, v in bands.items() if v] + (["none within 30 x%d" % later] if later else []) + (["check failed x%d" % failed] if failed else [])
    bits = (["pull after our sell: " + ", ".join(parts)] if parts else []) + (["pull BEFORE our sell x%d (each one halted the line)" % first] if first else [])
    return "; ".join(bits)


def pull_col(d):
    """the operator's first pull after our buy, in blocks; 'later': the check ran and found none within 30 blocks of our sell"""
    if d.get("pull_after_buy_blocks") is not None:
        return "+" + str(d["pull_after_buy_blocks"])
    if d.get("pull_check"):
        return "check failed"
    if "pull_after_buy_blocks" in d:                                         # the check ran (both receipts in, the buy filled) and found none
        return "later"
    return "-"


def exit_of(why):
    """the engine's sell reason in a few words"""
    w = why or ""
    for key, short in (("take profit", "take profit"), ("the bot's buy behind ours", "bot's buy behind ours"), ("a real-size buy behind ours", "real buy behind ours"),
                       ("the bot's buy reverts", "bot's buy reverts"), ("the bot's buy landed ahead", "bot ahead, same block"), ("the crowd's buy behind ours", "crowd behind ours"),
                       ("deadline", "deadline"), ("time fallback", "time fallback"), ("buy refused", "buy refused")):
        if w.startswith(key):
            return short
    return w.split(":")[0].split(" (")[0][:28] or "?"


def result_col(d):
    b = d.get("buy")
    if b == "no receipt":
        return "UNKNOWN"                                                       # no buy receipt within the timeout: it never went in, or the RPC failed
    if isinstance(b, dict) and b.get("status") == "reverted":
        return "buy reverted"
    if isinstance(b, dict) and b.get("filled") is False:                       # a V3 buy that took no token (a pulled pool: the relay kept its ETH)
        return "buy not filled"
    return pct(d["ret"]) if d.get("ret") is not None else "?"


def stake_label(f, eth_usd):
    if f["mode"] == "off" and not f["stake_eth"]:
        return "-"
    cap = "$%.0f" % (f["stake_eth"] * eth_usd) if f["stake_eth"] else "?"
    if f["auto"]:
        return ("auto $%.0f (up to %s)" % (f["auto_eth"] * eth_usd, cap)) if f["auto_eth"] is not None else "auto (up to %s)" % cap
    return cap + " fixed"


def v3_money(e, rpc):
    """the V3 relay's part of the money line (HANDOFF 16.22): ("", None) without a RELAY_V3 address in the env file (read as the engine reads
    it: quotes and spaces stripped, 0x or 0X optional, 40 hex digits) or when it is RELAY itself; its balance, or "?" when the read fails (then 0
    in the total)"""
    norm = lambda v: (lambda h: h[2:] if h.startswith("0x") else h)((v or "").strip().strip("'\"").strip().lower())
    r3 = norm(e.get("RELAY_V3"))
    if not re.fullmatch(r"[0-9a-f]{40}", r3) or r3 == norm(e.get("RELAY")):
        return "", None
    b = balance(rpc, "0x" + r3)
    return ", V3 relay %s ETH" % ("%.6f" % b if b is not None else "?"), b


def lines_table(fams, base, by, front, dry_by, eth_usd, cols):
    """each front line: LIVE, dry or off, its stake, then trades and $ after gas over the last hour, today (UTC), the window and every log
    kept (from the trades' own results; the engine's own day counters start again at each restart)"""
    names = [f["name"] for f in fams] + sorted(k for k in by if k not in {f["name"] for f in fams})   # a line traded before, not configured now
    cell = lambda ds: "%4d %9s" % (len(ds), usd(sum(d.get("pnl_usd") or 0 for d in ds)))
    print("\nLINES  (per period: trades, $ after gas; 'since' = every log kept)")
    print("  %-9s%-5s%-22s" % ("line", "", "stake") + "".join("%15s" % c for c, _ in cols))
    if not names:
        print("  no front line loaded (see the lines above)")
    for n in names:
        f = next((f for f in fams if f["name"] == n), None); ds = by.get(n, [])
        mode = f["mode"] if f else "off"; stake = stake_label(f, eth_usd) if f else "-"
        if ds and mode != "dry":
            row = "".join("%15s" % cell([d for d in ds if d.get("t", 0) >= t0]) for _, t0 in cols)
        elif mode == "LIVE":
            row = "%60s" % "no live trades yet"
        elif mode == "off":
            row = "%60s" % "off"
        else:                                                                  # a dry line: its scored decisions (its earlier live trades are under BY LINE)
            dd = dry_by.get(n, []); sc = [x["dry_ret"] for x in dd if x.get("dry_ret") is not None]
            row = "%60s" % (("dry: %d would-have-traded in %g h" % (len(dd), HOURS) + (", %d priced %s a trade" % (len(sc), pct(sum(sc) / len(sc))) if sc else "")) if dd else "dry: nothing is sent")
        print("  %-9s%-5s%-22s" % (n, mode, stake) + row)
    if len([n for n in names if by.get(n)]) > 1:
        print("  %-36s" % "all live trades" + "".join("%15s" % cell([d for d in front if d.get("t", 0) >= t0]) for _, t0 in cols))


def line_details(fams, by, dry_by, eth_usd):
    """one block per line: the live results (share up, $ a trade, average and worst return, the pulls, by stake band), a dry line's scoring"""
    names = [f["name"] for f in fams] + sorted(k for k in by if k not in {f["name"] for f in fams})
    first = True
    for n in names:
        ds = by.get(n, []); f = next((f for f in fams if f["name"] == n), None); dd = dry_by.get(n, [])
        if not ds and not dd:
            continue
        if first:
            print("\nBY LINE"); first = False
        if ds:
            rets = [d["ret"] for d in ds if d.get("ret") is not None]; u = [d.get("pnl_usd") or 0 for d in ds]
            print("  %s: %s, %.0f%% up, %s a trade" % (n, n_of(len(ds), "trade"), 100 * sum(1 for x in u if x > 0) / len(ds), usd(sum(u) / len(ds)))
                  + (", %s a trade on average, worst %s" % (pct(sum(rets) / len(rets)), pct(min(rets))) if rets else ""))
            ps = pull_summary(ds)
            if ps:
                print("    " + ps)
            bands = {}                                                         # the stake changes over time (the auto stake every trade): $ a trade in $5 bands
            for d in ds:
                if d.get("stake"):
                    k = 5 * int(d["stake"] / 1e18 * eth_usd // 5); bands.setdefault(k, []).append(d.get("pnl_usd") or 0)
            if len(bands) > 1:
                print("    by stake: " + "; ".join("$%d-%d: %s %s (%s a trade)" % (k, k + 5, n_of(len(g), "trade"), usd(sum(g)), usd(sum(g) / len(g))) for k, g in sorted(bands.items())))
        if dd and f and f["mode"] != "LIVE":
            sc = [x["dry_ret"] for x in dd if x.get("dry_ret") is not None]
            print("  %s dry run: %d would-have-traded, " % (n, len(dd)) + ("%d of %d priced from the chain up, %s a trade on average, worst %s" % (sum(1 for r in sc if r > 0), len(sc), pct(sum(sc) / len(sc)), pct(min(sc))) if sc else "none priced from the chain yet")
                  + "; the last at %s UTC" % hms(dd[-1]["t"]) + (": %s, %s" % (pct(dd[-1]["dry_ret"]), exit_of(dd[-1].get("sell_why"))) if dd[-1].get("dry_ret") is not None else ""))


def main():
    ev, st, flow, done_all = read_logs(HOURS); e = env(); eth_usd = num(e.get("ETH_USD"), 2570.0)
    active = subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"], stderr=subprocess.DEVNULL).returncode == 0
    dry = st.get("dry_run", True) if st else e.get("DRY_RUN", "1") != "0"      # no start line in any log: what the env file says
    now_ = flow if flow.get("t", 0) >= st.get("t", 0) else st                  # the engine's last word on its state: the last status line of this run, else the start line
    fams, base = families(st, e, now_)
    front = [d for d in done_all if d.get("entry") == "front"]
    by = {}
    for d in front:
        by.setdefault(d.get("fam") or base, []).append(d)                      # a front trade before families existed: the FRONT_* line's
    wf = {x.get("pid"): x for x in ev if x["ev"] == "would_fire"}
    dry_done = [x for x in ev if x["ev"] == "trade_done" and x.get("dry") and (x.get("fam") or wf.get(x.get("pid"), {}).get("entry") == "front")]   # a dry record has no entry: its would_fire has
    dry_by = {}
    for x in dry_done:
        dry_by.setdefault(x.get("fam") or base, []).append(x)
    now = time.time(); t0_all = front[0]["t"] if front else now
    cols = [("last hour", now - 3600), ("today (UTC)", now - now % 86400), ("last %g h" % HOURS, now - HOURS * 3600), ("since " + hm(t0_all)[:5], 0)]
    print("=" * 100)
    print("FLIP ENGINE  service %s   release %s   %s   %s" % ("RUNNING" if active else "STOPPED", st.get("release", "?"), "DRY RUN (nothing is sent)" if dry else "LIVE",
                                                              ("started %s UTC" % hm(st["t"])) if st else "no start line in " + LOG))
    print("report: the last %g h, to %s UTC" % (HOURS, hm(now)))
    halts = []
    if os.path.exists(HALT):
        halts.append("HALTED (all live trading): %s\n  to resume, once understood: sudo rm %s && sudo systemctl restart flip-engine" % (open(HALT).read().strip()[:120] or "(empty file)", HALT))
    elif now_.get("halted") and active:
        halts.append("HALTED in memory (all live trading): %s; the file is gone: sudo systemctl restart flip-engine" % str(now_["halted"])[:120])
    if os.path.exists(HALT + ".front"):
        halts.append("HALTED (every front line): %s\n  to resume, once understood: sudo rm %s.front && sudo systemctl restart flip-engine" % (open(HALT + ".front").read().strip()[:120] or "(empty file)", HALT))
    elif now_.get("front_halted") and active:
        halts.append("front lines OFF for this run: %s (sudo systemctl restart flip-engine)" % str(now_["front_halted"])[:120])
    for f in fams:
        p = HALT + ".front." + f["name"]
        if os.path.exists(p):
            halts.append("HALTED (%s only): %s\n  to resume, once understood: sudo rm %s && sudo systemctl restart flip-engine" % (f["name"], open(p).read().strip()[:120] or "(empty file)", p))
        elif (now_.get("fam_halted") or {}).get(f["name"]) and active:
            halts.append("%s HALTED in memory: %s; the file is gone: sudo systemctl restart flip-engine" % (f["name"], str(now_["fam_halted"][f["name"]])[:120]))
    if os.path.exists(HALT + ".follow") and e.get("FOLLOW", "1") != "0":
        halts.append("follow HALTED: %s (sudo rm %s.follow && sudo systemctl restart flip-engine)" % (open(HALT + ".follow").read().strip()[:120] or "(empty file)", HALT))
    print("\n".join(halts) if halts else "halted: no")
    if st.get("front_family_error"):
        print("FAMILIES NOT ALL LOADED: %s; tell Claude" % str(st["front_family_error"])[:160])
    lines_table(fams, base, by, front, dry_by, eth_usd, cols)
    if not ev:
        print("\nno engine events in the last %g hours: the engine is not running or not logging.  sudo systemctl status flip-engine --no-pager" % HOURS)
    # live trades: every front buy we sent in the window, with its result (or why there is none)
    all_fires = [x for x in ev if x["ev"] == "fire"]
    fires = [x for x in all_fires if x.get("entry") == "front"]
    done = [x for x in ev if x["ev"] == "trade_done" and not x.get("dry") and x.get("entry") == "front"]
    refused = [x for x in ev if x["ev"] == "buy_rejected"]
    rows = []; used = set()
    for f in fires:                                                            # a fire's result: the first trade_done with its nonce before that nonce fires again (a refused buy's nonce is used again)
        t1 = next((g["t"] for g in all_fires if g["t"] > f["t"] and g.get("nonce") == f.get("nonce")), float("inf"))
        d = next((x for x in done if f["t"] <= x["t"] < t1 and x.get("nonce") == f.get("nonce") and id(x) not in used), None)
        if d is not None:
            rows.append((f, d)); used.add(id(d)); continue
        r = next((x for x in refused if f["t"] <= x["t"] < t1 and x.get("pid") == f.get("pid")), None)
        if r is not None:
            err = (r.get("reply") or {}).get("error"); msg = err.get("message") if isinstance(err, dict) else r.get("reply")
            rows.append((f, "REFUSED by the node: " + str(msg)[:60]))
        else:
            rows.append((f, "in progress" if now - f["t"] < 120 else "NO RESULT LOGGED (sudo journalctl -u flip-engine)"))
    rows += [(None, d) for d in done if id(d) not in used]                     # its fire line was before the window
    rows.sort(key=lambda r: (r[0] or r[1])["t"])
    print("\nLIVE TRADES in the window: %d%s" % (len(rows), " (the last %d; the filled ones all count in the table above)" % LAST_TRADES if len(rows) > LAST_TRADES else ""))
    if rows:
        print("  %-15s %-8s %6s %12s %7s  %8s %12s  exit" % ("time (UTC)", "line", "stake", "result", "$", "sold at", "pull at"))
    for f, d in rows[-LAST_TRADES:]:
        x = d if isinstance(d, dict) else f; line = x.get("fam") or base
        stake = ("$%.0f" % (x["stake"] / 1e18 * eth_usd)) if x.get("stake") else "-"
        if isinstance(d, str):
            print("  %-15s %-8s %6s %12s %7s  %8s %12s  %s" % (hms(f["t"]), line, stake, "-", "-", "-", "-", d))
            continue
        sold = d.get("sell_after_buy_blocks", d.get("hold_blocks")); pull = d.get("pull_after_buy_blocks")
        first = d.get("pulled_before_sell")
        if first is None and pull is not None and sold is not None:                  # older releases did not log it: from the blocks
            first = True if pull < sold else (None if pull == sold else False)
        flag = "   <== THE PULL CAME FIRST" if first else ("   (same block as the pull: our sell got in first)" if pull is not None and pull == sold else "")
        print("  %-15s %-8s %6s %12s %+7.3f  %8s %12s  %s%s" % (hms(d["t"]), line, stake, result_col(d), d.get("pnl_usd") or 0.0, ("+" + str(sold)) if sold is not None else "-", pull_col(d), exit_of(d.get("sell_why")), flag))
    if rows:
        nores = sum(1 for _, d in rows if isinstance(d, str) and not d.startswith("REFUSED")); ref = sum(1 for _, d in rows if isinstance(d, str) and d.startswith("REFUSED"))
        print("  'sold at' and 'pull at' count blocks after our buy (0.1 s each); 'later' = no pull within 30 blocks of our sell"
              + ("; %d buy(s) refused by the node (nothing sent)" % ref if ref else "") + ("; %d buy(s) with no result logged" % nores if nores else ""))
    line_details(fams, by, dry_by, eth_usd)
    # the launches, per line
    arm = [x for x in ev if x["ev"] == "armed" and x.get("entry") == "front"]
    fired = {}
    for x in ev:
        if x["ev"] in ("fire", "would_fire") and x.get("entry") == "front":
            fired[x.get("fam") or base] = fired.get(x.get("fam") or base, 0) + 1
    per = {}
    for x in arm:
        per[x.get("fam") or base] = per.get(x.get("fam") or base, 0) + 1
    order = [f["name"] for f in fams] + sorted(k for k in set(per) | set(fired) if k not in {f["name"] for f in fams})
    print("\nlaunches seen %d" % len(arm) + ((": " + ", ".join("%s %d (fired %d)" % (n, per.get(n, 0), fired.get(n, 0)) for n in order if per.get(n) or fired.get(n))) if arm else "")
          + ("; the last at %s UTC" % hms(arm[-1]["t"]) if arm else " -- none: the operator has not launched (or its launches look different)"))
    nf = [x for x in arm if str(x.get("fingerprint", "")).startswith("new")]
    if nf:                                                                     # the bot changed its launch (traded unless the family pins its fingerprint)
        print("launches with a fingerprint not seen before: %d (the last at %s UTC, %s: %s); %s; tell Claude"
              % (len(nf), hms(nf[-1]["t"]), nf[-1].get("fam") or base, nf[-1]["fingerprint"][5:70], "ARMED TO TRADE" if nf[-1].get("eligible") else "not traded (pinned)"))
    fp = {x.get("pid") for x in arm}
    skips = [x for x in ev if x["ev"] == "skip" and (x.get("pid") in fp or str(x.get("why", "")).startswith(("front:", "wave:")))]
    if skips:
        reasons = {}
        for x in skips:
            why = str(x.get("why")); why = "halted (see above)" if why.startswith("halted") else why.split(" (")[0]
            reasons[why[:60]] = reasons.get(why[:60], 0) + 1
        top = sorted(reasons.items(), key=lambda kv: -kv[1])
        print("not traded: " + "; ".join("%s x%d" % kv for kv in top[:6]) + ("; %d other reasons" % (len(top) - 6) if len(top) > 6 else ""))
    # the dry lines' last decisions
    for f in fams:
        dd = dry_by.get(f["name"], [])
        if f["mode"] == "LIVE" or not dd:
            continue
        print("\n%s DRY RUN, the last %d of %d (nothing sent):" % (f["name"], min(3, len(dd)), len(dd)))
        for x in dd[-3:]:
            print("  %-15s %12s  %s" % (hms(x["t"]), pct(x["dry_ret"]) if x.get("dry_ret") is not None else "not priced", exit_of(x.get("sell_why"))))
    al = [x for x in ev if x["ev"] == "alarm"]
    if al:
        print("\nALARMS (%d%s):" % (len(al), ", the last 5" if len(al) > 5 else ""))
        for x in al[-5:]:
            print("  %s %s" % (hms(x["t"]), str(x.get("what"))[:150]))
    rpc = e.get("RPC_URL") or "https://rpc.mainnet.chain.robinhood.com"; w = e.get("WALLET"); r = e.get("RELAY")
    if not w or not r:
        print("\nmoney: WALLET or RELAY is not in %s (run with sudo)" % ENV)
    else:
        wb = balance(rpc, w); rb = balance(rpc, r)
        if wb is None or rb is None:
            print("\nmoney: the RPC did not answer; try again")
        else:
            part, r3b = v3_money(e, rpc)
            print("\nmoney: wallet %.6f ETH (gas), relay %.6f ETH (the stakes)%s; together about $%.2f at $%g/ETH"
                  % (wb, rb, part, (wb + rb + (r3b or 0.0)) * eth_usd, eth_usd))
    print("=" * 100)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:                                                    # | head closed the pipe: the rest is not wanted
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno()); sys.exit(0)
