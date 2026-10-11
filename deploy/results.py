#!/usr/bin/env python3
"""results.py: the flip engine's results in one screen. The engine's state (live or dry run, halted or not), each front line (a launch
family: v2.433, c1, v3.0, v3crowd, ...) with its stake and its live result over the last hour, today, the report's window and every log
kept, the launches seen per line, the last live trades, the dry lines' scored decisions, the alarms, and the money in the wallet and the relay.

    sudo python3 ~/v2pons/deploy/results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/results.py 72       # the last 72 hours
"""
import glob, gzip, json, os, subprocess, sys, time, urllib.request
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
LOG = "/var/log/flip/engine.jsonl"; ENV = "/etc/flip/engine.env"; HALT = "/var/log/flip/HALTED"
LAST_TRADES = 8                                                                # live trades listed one by one (the rest are in the table)
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
hm = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
usd = lambda u: f"{'+' if u >= 0 else '-'}${abs(u):.2f}"
n_of = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"


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


def families(st, e, flow):
    """the front lines as the engine's last start line lists them (release 0.9's families); before families existed, the one FRONT_* line.
    Each: name, live (its trades are sent), its stake in ETH (the auto stake's ceiling when the stake is automatic), the auto stake now"""
    dry_all = st.get("dry_run", e.get("DRY_RUN", "1") != "0") if st else e.get("DRY_RUN", "1") != "0"
    front_on = st.get("front", e.get("FRONT", "0") != "0") if st else e.get("FRONT", "0") != "0"
    front_dry = st.get("front_dry_run", e.get("FRONT_DRY_RUN", "1") != "0") if st else e.get("FRONT_DRY_RUN", "1") != "0"
    fams = st.get("front_families")
    if not fams:                                                               # an older start line: the FRONT_* line alone
        fams = [{"name": e.get("FRONT_FAMILY_NAME", "v2.433"), "stake_eth": num(st.get("front_stake_eth", e.get("FRONT_STAKE_ETH")), 0), "dry_run": False}]
    auto = flow.get("auto_stake_eth") or {} if flow.get("t", 0) >= st.get("t", 0) else {}   # the engine's last status line, if it is from this run
    out = []
    for f in fams:
        live = front_on and not dry_all and not front_dry and not f.get("dry_run") and f.get("dex") != "v3"   # a V3 family is dry whatever it says
        out.append({"name": f["name"], "live": live, "stake_eth": num(f.get("stake_eth"), 0), "auto": f["name"] in auto, "auto_eth": auto.get(f["name"]),
                    "dex": f.get("dex", "v4"), "trigger": f.get("trigger")})
    return out


def pull_summary(ds):
    """the operator's reaction to the line's trades: its pull, in blocks after our sell landed, in four bands, and the pulls before our sell"""
    bands = {"0-1": 0, "2-3": 0, "4-9": 0, "10+": 0}; first = later = 0
    for d in ds:
        sold, pull = d.get("sell_after_buy_blocks"), d.get("pull_after_buy_blocks")
        if d.get("pulled_before_sell") or (pull is not None and sold is not None and pull < sold):
            first += 1
        elif pull is not None and sold is not None:
            g = pull - sold; bands["0-1" if g <= 1 else "2-3" if g <= 3 else "4-9" if g <= 9 else "10+"] += 1
        elif "pull_after_buy_blocks" in d:
            later += 1
    if not (first or later or any(bands.values())):
        return ""
    parts = [f"{k} blocks x{v}" for k, v in bands.items() if v] + ([f"none within 30 x{later}"] if later else [])
    bits = (["pull after our sell: " + ", ".join(parts)] if parts else []) + ([f"pull BEFORE our sell x{first}  <== halts"] if first else [])
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
    return f"{100 * d['ret']:+.1f}%" if d.get("ret") is not None else "?"


def lines_table(fams, done, ev, e, eth_usd):
    """each front line: LIVE or dry, its stake, then trades and $ after gas over the last hour, today (UTC), the window and every log kept
    (from the trades' own results; the engine's own day counters start again at each restart); under it one detail line per line"""
    base = fams[0]["name"] if fams else "v2.433"
    fam_of = lambda d: d.get("fam") or base                                    # a front trade before families existed: the FRONT_* line's
    front = [d for d in done if d.get("entry") == "front"]
    by = {}
    for d in front:
        by.setdefault(fam_of(d), []).append(d)
    names = [f["name"] for f in fams] + sorted(k for k in by if k not in {f["name"] for f in fams})   # a line traded before, not configured now
    now = time.time(); t0_all = front[0]["t"] if front else now
    cols = [("last hour", now - 3600), ("today (UTC)", now - now % 86400), (f"last {HOURS:g} h", now - HOURS * 3600), (f"since {hm(t0_all)[:5]}", 0)]
    cell = lambda ds: f"{len(ds):>4} {usd(sum(d.get('pnl_usd') or 0 for d in ds)):>9s}"
    dry_done = [x for x in ev if x["ev"] == "trade_done" and x.get("dry")]
    print("\nLINES  (per period: trades, $ after gas; 'since' = every log kept)")
    print(f"  {'line':9s}{'':5s}{'stake':22s}" + "".join(f"{c:>15s}" for c, _ in cols))
    for n in names:
        f = next((f for f in fams if f["name"] == n), None); ds = by.get(n, [])
        if f is None:
            mode, stake = "off", "-"
        else:
            mode = "LIVE" if f["live"] else "dry"
            if f["auto"] and f["auto_eth"] is not None:
                stake = f"auto ${f['auto_eth'] * eth_usd:.0f} (up to ${f['stake_eth'] * eth_usd:.0f})"
            elif not f["stake_eth"]:
                stake = "?"
            else:
                stake = f"${f['stake_eth'] * eth_usd:.0f}" + (" fixed" if f["trigger"] else "")
        if ds:
            row = "".join(f"{cell([d for d in ds if d.get('t', 0) >= t0]):>15s}" for _, t0 in cols)
        elif f and f["live"]:
            row = f"{'no live trades yet':>60s}"
        else:
            dd = [x for x in dry_done if (x.get("fam") or base) == n]; sc = [x["dry_ret"] for x in dd if x.get("dry_ret") is not None]
            row = f"{(f'dry: {len(dd)} would-have-traded in {HOURS:g} h' + (f', {len(sc)} priced {100 * sum(sc) / len(sc):+.1f}% a trade' if sc else '')) if dd else 'dry: nothing is sent':>60s}"
        print(f"  {n:9s}{mode:5s}{stake:22s}" + row)
    if len([n for n in names if by.get(n)]) > 1:
        print(f"  {'all lines':36s}" + "".join(f"{cell([d for d in front if d.get('t', 0) >= t0]):>15s}" for _, t0 in cols))
    for n in names:                                                            # one line of detail per line: live results, then the dry run's scoring
        ds = by.get(n, [])
        if ds:
            rets = [d["ret"] for d in ds if d.get("ret") is not None]; u = [d.get("pnl_usd") or 0 for d in ds]
            print(f"  {n}: {n_of(len(ds), 'trade')}, {sum(1 for x in u if x > 0) / len(ds):.0%} up, {usd(sum(u) / len(ds))} a trade"
                  + (f", {100 * sum(rets) / len(rets):+.1f}% a trade on average, worst {100 * min(rets):+.1f}%" if rets else ""))
            ps = pull_summary(ds)
            if ps:
                print(f"    {ps}")
            stakes = {}
            for d in ds:
                if d.get("stake"):
                    stakes.setdefault(round(d["stake"] / 1e18 * eth_usd), []).append(d.get("pnl_usd") or 0)
            if len(stakes) > 1:
                print("    by stake: " + "; ".join(f"${k}: {n_of(len(g), 'trade')} {usd(sum(g))} ({usd(sum(g) / len(g))} a trade)" for k, g in sorted(stakes.items())))
        dd = [x for x in dry_done if (x.get("fam") or base) == n]
        f = next((f for f in fams if f["name"] == n), None)
        if dd and f and not f["live"]:
            sc = [x["dry_ret"] for x in dd if x.get("dry_ret") is not None]
            print(f"  {n} dry run: " + (f"{sum(1 for r in sc if r > 0)} of {len(sc)} priced trades up, worst {100 * min(sc):+.1f}%; " if sc else "none priced from the chain yet; ")
                  + f"the last at {hms(dd[-1]['t'])} UTC" + (f": {100 * dd[-1]['dry_ret']:+.1f}%, {exit_of(dd[-1].get('sell_why'))}" if dd[-1].get("dry_ret") is not None else ""))
    return base


def main():
    ev, st, flow, done_all = read_logs(HOURS); e = env(); eth_usd = num(e.get("ETH_USD"), 2570.0)
    active = subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"], stderr=subprocess.DEVNULL).returncode == 0
    dry = st.get("dry_run", True) if st else e.get("DRY_RUN", "1") != "0"      # no start line in any log: what the env file says
    fams = families(st, e, flow); fnow = flow if flow.get("t", 0) >= st.get("t", 0) else {}   # the engine's last status line, if it is from this run
    print("=" * 100)
    print(f"FLIP ENGINE  service {'RUNNING' if active else 'STOPPED'}   release {st.get('release', '?')}   {'DRY RUN (nothing is sent)' if dry else 'LIVE'}   "
          + (f"started {hm(st['t'])} UTC   " if st else f"no start line in {LOG}   ") + f"report: the last {HOURS:g} h to {hm(time.time())} UTC")
    halts = []
    if os.path.exists(HALT):
        halts.append(f"HALTED (all live trading): {open(HALT).read().strip()[:120] or '(empty file)'}\n  to resume, once understood: sudo rm {HALT} && sudo systemctl restart flip-engine")
    elif fnow.get("halted"):
        halts.append(f"HALTED in memory (all live trading, {hms(fnow['t'])} UTC: {str(fnow['halted'])[:120]}); the file is gone: sudo systemctl restart flip-engine")
    if os.path.exists(HALT + ".front"):
        halts.append(f"HALTED (every front line): {open(HALT + '.front').read().strip()[:120] or '(empty file)'}\n  to resume, once understood: sudo rm {HALT}.front && sudo systemctl restart flip-engine")
    elif fnow.get("front_halted"):
        halts.append(f"front lines OFF for this run: {str(fnow['front_halted'])[:120]} (sudo systemctl restart flip-engine)")
    for f in fams:
        p = HALT + ".front." + f["name"]
        if os.path.exists(p):
            halts.append(f"HALTED ({f['name']} only): {open(p).read().strip()[:120] or '(empty file)'}\n  to resume, once understood: sudo rm {p} && sudo systemctl restart flip-engine")
        elif (fnow.get("fam_halted") or {}).get(f["name"]):
            halts.append(f"{f['name']} HALTED in memory: {str(fnow['fam_halted'][f['name']])[:120]}; the file is gone: sudo systemctl restart flip-engine")
    if os.path.exists(HALT + ".follow") and e.get("FOLLOW", "1") != "0":
        halts.append(f"follow HALTED: {open(HALT + '.follow').read().strip()[:120] or '(empty file)'} (sudo rm {HALT}.follow && sudo systemctl restart flip-engine)")
    print("\n".join(halts) if halts else "halted: no")
    if st.get("front_family_error"):
        print(f"FAMILIES NOT ALL LOADED: {str(st['front_family_error'])[:160]}; tell Claude")
    base = lines_table(fams, done_all, ev, e, eth_usd)
    if not ev:
        print(f"\nno engine events in the last {HOURS:g} hours: the engine is not running or not logging.  sudo systemctl status flip-engine --no-pager")
    arm = [x for x in ev if x["ev"] == "armed" and x.get("entry", "front") == "front"]
    fired = {}
    for x in ev:
        if x["ev"] in ("fire", "would_fire") and x.get("entry") == "front":
            fired[x.get("fam") or base] = fired.get(x.get("fam") or base, 0) + 1
    per = {}
    for x in arm:
        per[x.get("fam") or base] = per.get(x.get("fam") or base, 0) + 1
    order = [f["name"] for f in fams] + sorted(k for k in set(per) | set(fired) if k not in {f["name"] for f in fams})
    print(f"\nlaunches seen {len(arm)}" + (": " + ", ".join(f"{n} {per.get(n, 0)} (fired {fired.get(n, 0)})" for n in order if per.get(n) or fired.get(n)) if arm else "")
          + (f"; the last at {hms(arm[-1]['t'])} UTC" if arm else " -- none: the operator has not launched (or its launches look different)"))
    nf = [x for x in arm if str(x.get("fingerprint", "")).startswith("new")]
    if nf:                                                                     # the bot changed its launch (traded unless the family pins its fingerprint)
        print(f"launches with a fingerprint not seen before: {len(nf)} (the last at {hms(nf[-1]['t'])} UTC, {nf[-1].get('fam') or base}: {nf[-1]['fingerprint'][5:70]}); "
              f"{'TRADED' if nf[-1].get('eligible') else 'not traded'}; tell Claude")
    skips = [x for x in ev if x["ev"] == "skip"]
    if skips:
        reasons = {}
        for x in skips:
            why = str(x.get("why")); why = "halted (see above)" if why.startswith("halted") else why.split(" (")[0]
            reasons[why[:60]] = reasons.get(why[:60], 0) + 1
        top = sorted(reasons.items(), key=lambda kv: -kv[1])
        print("not traded: " + "; ".join(f"{k} x{v}" for k, v in top[:6]) + (f"; {len(top) - 6} other reasons" if len(top) > 6 else ""))
    # live trades: every buy we sent, with its result (or why there is none)
    fires = [x for x in ev if x["ev"] == "fire"]
    done = [x for x in ev if x["ev"] == "trade_done" and not x.get("dry")]
    refused = [x for x in ev if x["ev"] == "buy_rejected"]
    rows = []; used = set()
    for i, f in enumerate(fires):                                              # a fire's result: the first trade_done with its nonce, before that nonce fires again (a refused buy's nonce is used again)
        t1 = next((g["t"] for g in fires[i + 1:] if g.get("nonce") == f.get("nonce")), float("inf"))
        d = next((x for x in done if f["t"] <= x["t"] < t1 and x.get("nonce") == f.get("nonce") and id(x) not in used), None)
        if d is not None:
            rows.append((f, d)); used.add(id(d)); continue
        r = next((x for x in refused if f["t"] <= x["t"] < t1 and x.get("pid") == f.get("pid")), None)
        if r is not None:
            err = (r.get("reply") or {}).get("error"); msg = err.get("message") if isinstance(err, dict) else r.get("reply")
            rows.append((f, "REFUSED by the node: " + str(msg)[:60]))
        else:
            rows.append((f, "in progress" if time.time() - f["t"] < 120 else "NO RESULT LOGGED (sudo journalctl -u flip-engine)"))
    rows += [(None, d) for d in done if id(d) not in used]                     # its fire line was before the window
    rows.sort(key=lambda r: (r[0] or r[1])["t"])
    print(f"\nLIVE TRADES in the window: {len(rows)}" + (f" (the last {LAST_TRADES}; every one counts in the table above)" if len(rows) > LAST_TRADES else ""))
    if rows:
        print(f"  {'time (UTC)':15s} {'line':8s} {'stake':>6s} {'result':>12s} {'$':>7s}  {'sold at':>8s} {'pull at':>12s}  exit")
    for f, d in rows[-LAST_TRADES:]:
        x = d if isinstance(d, dict) else f; line = (x.get("fam") or base) if x.get("entry", "front") == "front" else (x.get("entry") or "?")
        stake = f"${x['stake'] / 1e18 * eth_usd:.0f}" if x.get("stake") else "-"
        if isinstance(d, str):
            print(f"  {hms(f['t']):15s} {line:8s} {stake:>6s} {'-':>12s} {'-':>7s}  {'-':>8s} {'-':>12s}  {d}")
            continue
        sold = d.get("sell_after_buy_blocks", d.get("hold_blocks")); pull = d.get("pull_after_buy_blocks")
        first = d.get("pulled_before_sell")
        if first is None and pull is not None and sold is not None:                  # older releases did not log it: from the blocks
            first = True if pull < sold else (None if pull == sold else False)
        why = exit_of(d.get("sell_why"))
        flag = "   <== THE PULL CAME FIRST" if first else ("   (same block as the pull: our sell got in first)" if pull is not None and pull == sold else "")
        print(f"  {hms(d['t']):15s} {line:8s} {stake:>6s} {result_col(d):>12s} {(d.get('pnl_usd') or 0.0):+7.3f}  {'+' + str(sold) if sold is not None else '-':>8s} {pull_col(d):>12s}  {why}{flag}")
    if rows:
        nores = sum(1 for _, d in rows if isinstance(d, str) and not d.startswith("REFUSED")); ref = sum(1 for _, d in rows if isinstance(d, str) and d.startswith("REFUSED"))
        print("  'sold at' and 'pull at' count blocks after our buy (0.1 s each); 'later' = no pull within 30 blocks of our sell"
              + (f"; {ref} buy(s) refused by the node (nothing sent)" if ref else "") + (f"; {nores} buy(s) with no result logged" if nores else ""))
    # the dry lines' last decisions
    dry_done = [x for x in ev if x["ev"] == "trade_done" and x.get("dry")]
    for f in fams:
        if f["live"]:
            continue
        dd = [x for x in dry_done if (x.get("fam") or base) == f["name"]]
        if not dd:
            continue
        print(f"\n{f['name']} DRY RUN, the last {min(3, len(dd))} of {len(dd)} (nothing sent; the scoring is in the table above):")
        for x in dd[-3:]:
            print(f"  {hms(x['t']):15s} {(f'{100 * x['dry_ret']:+.1f}%' if x.get('dry_ret') is not None else 'not priced'):>12s}  {exit_of(x.get('sell_why'))}")
    al = [x for x in ev if x["ev"] == "alarm"]
    if al:
        print(f"\nALARMS ({len(al)}" + (", the last 5" if len(al) > 5 else "") + "):")
        for x in al[-5:]:
            print(f"  {hms(x['t'])} {str(x.get('what'))[:150]}")
    rpc = e.get("RPC_URL") or "https://rpc.mainnet.chain.robinhood.com"; w = e.get("WALLET"); r = e.get("RELAY")
    if not w or not r:
        print(f"\nmoney: WALLET or RELAY is not in {ENV} (run with sudo)")
    else:
        wb = balance(rpc, w); rb = balance(rpc, r)
        if wb is None or rb is None:
            print("\nmoney: the RPC did not answer; try again")
        else:
            print(f"\nmoney: wallet {wb:.6f} ETH (gas), relay {rb:.6f} ETH (the stakes); together about ${(wb + rb) * eth_usd:.2f} at ${eth_usd:g}/ETH")
    print("=" * 100)


if __name__ == "__main__":
    main()
