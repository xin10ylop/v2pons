#!/usr/bin/env python3
"""results.py: the flip engine's results in one screen. The engine's state (live or dry run, halted or not), the launches it saw,
every trade with its result, the totals, and the money in the wallet and the relay.

    sudo python3 ~/v2pons/deploy/results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/results.py 72       # the last 72 hours
"""
import glob, gzip, json, os, subprocess, sys, time, urllib.request
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
LOG = "/var/log/flip/engine.jsonl"; ENV = "/etc/flip/engine.env"; HALT = "/var/log/flip/HALTED"
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))


def read_logs(hours):
    """the events in the window, and the engine's last start and status lines whenever they were (a start before the window still
    says how it runs)"""
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out = []; last = {}
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


def balance(rpc, addr):
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(rpc, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [addr, "latest"]}).encode(),
                                                                    {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}), timeout=5))
        return int(r["result"], 16) / 1e18
    except Exception:
        return None


def pull_col(d):
    """the operator's first pull after our buy, in blocks; 'later': the check ran and found none within 30 blocks of our sell"""
    if d.get("pull_after_buy_blocks") is not None:
        return "+" + str(d["pull_after_buy_blocks"])
    if d.get("pull_check"):
        return "check failed"
    if "pull_after_buy_blocks" in d:                                         # the check ran (both receipts in, the buy filled) and found none
        return "later"
    return "-"


def result_col(d):
    b = d.get("buy")
    if b == "no receipt":
        return "UNKNOWN"                                                       # no buy receipt within the timeout: it never went in, or the RPC failed
    if isinstance(b, dict) and b.get("status") == "reverted":
        return "buy reverted"
    return f"{100 * d['ret']:+.1f}%" if d.get("ret") is not None else "?"


def main():
    ev, st, flow = read_logs(HOURS); e = env()
    active = subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"], stderr=subprocess.DEVNULL).returncode == 0
    if st:
        dry = st.get("dry_run", True)
    else:                                                                      # no start line in any log: what the env file says
        dry = e.get("DRY_RUN", "1") != "0"
    entry = st.get("entry") or e.get("ENTRY", "follow"); mx = st.get("max_trades_per_day") or e.get("MAX_TRADES_PER_DAY", "10")
    print("=" * 100)
    print(f"FLIP ENGINE  service {'RUNNING' if active else 'STOPPED'}   release {st.get('release', '?')}   {'DRY RUN (nothing is sent)' if dry else 'LIVE'}   "
          f"entry {entry}   max {mx} trades a day")
    if os.path.exists(HALT):
        why = open(HALT).read().strip() or "(empty file)"
        print(f"HALTED: {why}\n  to resume, once understood: sudo rm {HALT} && sudo systemctl restart flip-engine")
    elif flow.get("halted") and flow.get("t", 0) >= st.get("t", 0):
        print(f"HALTED in memory (its last status line, {hms(flow['t'])} UTC: {str(flow['halted'])[:120]});\n  the halt file is gone but the engine keeps the halt until: sudo systemctl restart flip-engine")
    else:
        print("halted: no")
    if st.get("front") or e.get("FRONT", "0") != "0":                                  # release 0.9: the front strategy has its own switch, stake and halt
        fdry = dry or st.get("front_dry_run", e.get("FRONT_DRY_RUN", "1") != "0")
        print(f"front strategy: ON, {'DRY RUN (nothing sent)' if fdry else 'LIVE'}, stake {st.get('front_stake_eth', e.get('FRONT_STAKE_ETH', '?'))} ETH, "
              f"max {st.get('front_max_per_day', e.get('FRONT_MAX_PER_DAY', '?'))} a day"
              + (f";  HALTED: {open(HALT + '.front').read().strip()[:120] or '(empty file)'}  (sudo rm {HALT}.front && sudo systemctl restart flip-engine)" if os.path.exists(HALT + ".front") else ";  halted: no"))
    if st:
        print(f"last start {hms(st['t'])} UTC; this report covers the last {HOURS:g} hours (to {hms(time.time())} UTC)")
    else:
        print(f"no start line in the logs ({LOG}): the mode above is the env file's ({ENV})")
    if not ev:
        print(f"\nno engine events in the last {HOURS:g} hours: the engine is not running or not logging.  sudo systemctl status flip-engine --no-pager")
    arm = [x for x in ev if x["ev"] == "armed"]; elig = [x for x in arm if x.get("eligible")]
    entries = {}
    for x in elig:
        entries[x.get("entry", "follow")] = entries.get(x.get("entry", "follow"), 0) + 1
    print(f"\nlaunches seen {len(arm)} (tradable {len(elig)}" + ("".join(f", {k} {v}" for k, v in sorted(entries.items())) if entry == "auto" else "") + ")"
          + (f", the last at {hms(arm[-1]['t'])} UTC" if arm else " -- none: the operator has not launched (or its launches look different)"))
    skips = [x for x in ev if x["ev"] == "skip"]
    if skips:
        reasons = {}
        for x in skips: reasons[str(x.get("why"))[:60]] = reasons.get(str(x.get("why"))[:60], 0) + 1
        print("not traded: " + "; ".join(f"{k} x{v}" for k, v in reasons.items()))
    # live trades: every buy we sent, with its result (or why there is none)
    fires = [x for x in ev if x["ev"] == "fire"]
    done = [x for x in ev if x["ev"] == "trade_done" and not x.get("dry")]
    refused = [x for x in ev if x["ev"] == "buy_rejected"]
    rows = []; used = set()
    for i, f in enumerate(fires):                                              # a fire's result comes before the next fire (a refused buy's nonce is used again)
        t1 = fires[i + 1]["t"] if i + 1 < len(fires) else float("inf")
        d = next((x for x in done if f["t"] <= x["t"] < t1 and x.get("nonce") == f.get("nonce")), None)
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
    print(f"\nLIVE TRADES: {len(rows)}")
    if rows:
        print(f"  {'time (UTC)':15s} {'fee':>7s} {'result':>12s} {'$':>7s}  {'sold at':>8s} {'pull at':>12s}  exit")
    tot = 0.0; won = lost = pulled = 0; nores = 0
    for f, d in rows:
        if isinstance(d, str):
            nores += 1
            print(f"  {hms(f['t']):15s} {f.get('fee', 0) / 1e4:6.3f}% {'-':>12s} {'-':>7s}  {'-':>8s} {'-':>12s}  {f.get('entry') or ''}  {d}")
            continue
        usd = d.get("pnl_usd") or 0.0; tot += usd
        sold = d.get("sell_after_buy_blocks", d.get("hold_blocks")); pull = d.get("pull_after_buy_blocks")
        first = d.get("pulled_before_sell")
        if first is None and pull is not None and sold is not None:                  # older releases did not log it: from the blocks
            first = True if pull < sold else (None if pull == sold else False)
        won += 1 if usd > 0 else 0; lost += 1 if usd <= 0 else 0; pulled += 1 if first else 0
        why = ((d.get("entry") + ", ") if d.get("entry") else "") + (d.get("sell_why") or "").split(":")[0]
        flag = "   <== THE PULL CAME FIRST" if first else ("   (same block as the pull: our sell got in first)" if pull is not None and pull == sold else "")
        print(f"  {hms(d['t']):15s} {d.get('fee', 0) / 1e4:6.3f}% {result_col(d):>12s} {usd:+7.3f}  {'+' + str(sold) if sold is not None else '-':>8s} {pull_col(d):>12s}  {why}{flag}")
    if rows:
        print(f"  TOTAL {'+' if tot >= 0 else '-'}${abs(tot):.3f} ({won + lost} trades: {won} up, {lost} flat or down; pulls before our sell: {pulled}"
              + (f"; {nores} buy(s) with no result" if nores else "") + ")")
        print("  'sold at' and 'pull at' count blocks after our buy (0.1 s each): every sell should land before the pull;")
        print("  'later' = no pull within 30 blocks of our sell (it came after, on the operator's own schedule); UNKNOWN = no buy receipt")
    if rows:
        by = {}
        for f_, d in rows:
            if isinstance(d, dict):
                k = d.get("entry") or "follow"; n_, u_ = by.get(k, (0, 0.0)); by[k] = (n_ + 1, u_ + (d.get("pnl_usd") or 0.0))
        if len(by) > 1:
            print("  by strategy: " + "; ".join(f"{k} {n_} trades {'+' if u_ >= 0 else '-'}${abs(u_):.3f}" for k, (n_, u_) in sorted(by.items())))
    # the dry run's decisions
    wf = {x["pid"]: x for x in ev if x["ev"] == "would_fire"}; ws = [x for x in ev if x["ev"] == "would_sell"]
    fws = [x for x in ws if wf.get(x.get("pid"), {}).get("entry") == "front"]
    if fws:                                                                    # the front strategy's dry run: up to ~330 decisions a day, so a summary
        tps = [x["tp_ret"] for x in fws if x.get("tp_ret") is not None]
        print(f"\nFRONT DRY RUN: {sum(1 for x in wf.values() if x.get('entry') == 'front')} would-buys, {len(fws)} would-sells: {len(tps)} on the volume bot's buy"
              + (f" (priced {100 * sum(tps) / len(tps):+.1f}% on average, worst {100 * min(tps):+.1f}%)" if tps else "") + f", {len(fws) - len(tps)} at the deadline")
        for x in fws[-5:]:
            print(f"  {hms(x['t']):15s} would sell {x.get('after_buy') if x.get('after_buy') is not None else '?'} block(s) after the buy: {(x.get('why') or '').split(':')[0]}"
                  + (f", priced {100 * x['tp_ret']:+.1f}%" if x.get("tp_ret") is not None else ""))
    ws = [x for x in ws if x not in fws]; wf = {k: v for k, v in wf.items() if v.get("entry") != "front"}
    if wf:
        print(f"\nDRY-RUN DECISIONS (nothing sent): {len(wf)}")
        for x in ws:
            tp = x.get("tp_ret")
            print(f"  {hms(x['t']):15s} would sell {x.get('after_buy') if x.get('after_buy') is not None else '?'} block(s) after the planned buy: {(x.get('why') or '').split(':')[0]}" + (f", priced {100 * tp:+.1f}%" if tp is not None else ""))
    al = [x for x in ev if x["ev"] == "alarm"]
    if al:
        print(f"\nALARMS ({len(al)}" + (", the last 5" if len(al) > 5 else "") + "):")
        for x in al[-5:]:
            print(f"  {hms(x['t'])} {str(x.get('what'))[:150]}")
    rpc = e.get("RPC_URL") or "https://rpc.mainnet.chain.robinhood.com"; w = e.get("WALLET"); r = e.get("RELAY")
    try:
        eth_usd = float(e.get("ETH_USD", "2570"))
    except ValueError:
        eth_usd = 2570.0
    if not w or not r:
        print(f"\nmoney: WALLET or RELAY is not in {ENV} (run with sudo)")
    else:
        wb = balance(rpc, w); rb = balance(rpc, r)
        if wb is None or rb is None:
            print(f"\nmoney: the RPC did not answer ({rpc}); try again")
        else:
            print(f"\nmoney: wallet {wb:.6f} ETH (gas), relay {rb:.6f} ETH (stake {e.get('STAKE_ETH', '?')}); together about ${(wb + rb) * eth_usd:.2f} at ${eth_usd:g}/ETH")
    print("=" * 100)


if __name__ == "__main__":
    main()
