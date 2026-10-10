#!/usr/bin/env python3
"""results.py: the flip engine's results in one screen. The engine's state (live or dry run, halted or not), the launches it saw,
every trade with its result, the totals, and the money in the wallet and the relay.

    sudo python3 ~/v2pons/deploy/results.py          # the last 24 hours
    sudo python3 ~/v2pons/deploy/results.py 72       # the last 72 hours
"""
import glob, gzip, json, os, subprocess, sys, time, urllib.request
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
LOG = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/review06_user/sc/live_long_running/engine.jsonl"; ENV = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/review06_user/sc/live_long_running/engine.env"; HALT = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/review06_user/sc/live_long_running/HALTED"; ETH_USD = 2570.0
hms = lambda t: time.strftime("%m-%d %H:%M:%S", time.gmtime(t))


def events(hours):
    t_lo = time.time() - hours * 3600
    files = sorted(glob.glob(LOG + ".*"), key=lambda f: (f.endswith(".gz"), f), reverse=True) + [LOG]
    out = []
    for f in files:
        try:
            for line in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("t", 0) >= t_lo:
                    out.append(e)
        except FileNotFoundError:
            pass
    return sorted(out, key=lambda e: e.get("t", 0))


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
                                                                    {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}), timeout=10))
        return int(r["result"], 16) / 1e18
    except Exception:
        return None


def main():
    ev = events(HOURS); e = env()
    active = subprocess.run(["systemctl", "is-active", "--quiet", "flip-engine"], stderr=subprocess.DEVNULL).returncode == 0
    start = [x for x in ev if x["ev"] == "start"]; st = start[-1] if start else {}
    halted = open(HALT).read().strip() if os.path.exists(HALT) else None
    print("=" * 100)
    print(f"FLIP ENGINE  service {'RUNNING' if active else 'STOPPED'}   release {st.get('release', '?')}   {'DRY RUN (nothing is sent)' if st.get('dry_run', True) else 'LIVE'}   "
          f"entry {st.get('entry', 'follow')}   max {st.get('max_trades_per_day', '?')} trades a day")
    print(f"HALTED: {halted}   (sudo rm {HALT} && sudo systemctl restart flip-engine, once understood)" if halted else "halted: no")
    if st: print(f"last start {hms(st['t'])} UTC; this report covers the last {HOURS:g} hours (to {hms(time.time())} UTC)")
    arm = [x for x in ev if x["ev"] == "armed"]; elig = [x for x in arm if x.get("eligible")]
    print(f"\nlaunches seen {len(arm)} (tradable {len(elig)})" + (f", the last at {hms(arm[-1]['t'])} UTC" if arm else " -- none: the operator has not launched (or its launches look different)"))
    skips = [x for x in ev if x["ev"] == "skip"]
    if skips:
        reasons = {}
        for x in skips: reasons[str(x.get("why"))[:60]] = reasons.get(str(x.get("why"))[:60], 0) + 1
        print("not traded: " + "; ".join(f"{k} x{v}" for k, v in reasons.items()))
    # live trades
    done = [x for x in ev if x["ev"] == "trade_done" and not x.get("dry")]
    print(f"\nLIVE TRADES: {len(done)}")
    if done:
        print(f"  {'time (UTC)':15s} {'fee':>7s} {'result':>8s} {'$':>7s}  {'sold at':>8s} {'pull at':>8s}  exit")
    tot = 0.0; won = lost = pulled = 0
    for d in done:
        ret = d.get("ret"); usd = d.get("pnl_usd") or 0.0; tot += usd
        sold = d.get("sell_after_buy_blocks", d.get("hold_blocks")); pull = d.get("pull_after_buy_blocks")
        first = d.get("pulled_before_sell")
        if first is None and pull is not None and sold is not None:                  # older releases did not log it: from the blocks
            first = True if pull < sold else (None if pull == sold else False)
        won += 1 if usd > 0 else 0; lost += 1 if usd <= 0 else 0; pulled += 1 if first else 0
        why = ((d.get("entry") + ", ") if d.get("entry") else "") + (d.get("sell_why") or "").split(":")[0]
        res = "no fill" if ret is None else f"{100 * ret:+.1f}%"
        flag = "   <== THE PULL CAME FIRST" if first else ("   (same block as the pull: our sell got in first)" if pull is not None and pull == sold and usd > -1 else "")
        print(f"  {hms(d['t']):15s} {d.get('fee', 0) / 1e4:6.3f}% {res:>8s} {usd:+7.3f}  {'+' + str(sold) if sold is not None else '-':>8s} {'+' + str(pull) if pull is not None else 'later':>8s}  {why}{flag}")
    if done:
        print(f"  TOTAL {'+' if tot >= 0 else '-'}${abs(tot):.3f} ({len(done)} trades: {won} up, {lost} flat or down; pulls before our sell: {pulled})")
        print("  'sold at' and 'pull at' count blocks after our buy (0.1 s each): every sell should land before the pull;")
        print("  'later' = no pull within 30 blocks of our sell (it came after, on the operator's own schedule)")
    # the dry run's decisions
    wf = {x["pid"]: x for x in ev if x["ev"] == "would_fire"}; ws = [x for x in ev if x["ev"] == "would_sell"]
    if wf:
        print(f"\nDRY-RUN DECISIONS (nothing sent): {len(wf)}")
        for x in ws:
            tp = x.get("tp_ret")
            print(f"  {hms(x['t']):15s} would sell {x.get('after_buy') if x.get('after_buy') is not None else '?'} block(s) after the planned buy: {(x.get('why') or '').split(':')[0]}" + (f", priced {100 * tp:+.1f}%" if tp is not None else ""))
    al = [x for x in ev if x["ev"] == "alarm"]
    if al:
        print(f"\nALARMS: {len(al)}, the last: {hms(al[-1]['t'])} {str(al[-1].get('what'))[:150]}")
    rpc = e.get("RPC_URL") or "https://rpc.mainnet.chain.robinhood.com"; w = e.get("WALLET"); r = e.get("RELAY")
    wb = balance(rpc, w) if w else None; rb = balance(rpc, r) if r else None
    print(f"\nmoney: wallet {wb if wb is None else f'{wb:.6f}'} ETH (gas), relay {rb if rb is None else f'{rb:.6f}'} ETH (stake {e.get('STAKE_ETH', '?')})"
          + (f"; together about ${(wb + rb) * ETH_USD:.2f}" if wb is not None and rb is not None else ""))
    print("=" * 100)


if __name__ == "__main__":
    main()
