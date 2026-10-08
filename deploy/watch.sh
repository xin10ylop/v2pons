#!/bin/bash
# watch.sh: the flip engine's trades as they happen, one line per step, a beep on every finished trade. Ctrl-C to stop; it does not
# touch the engine. In tmux it survives the SSH session:  tmux new -s watch 'sudo bash ~/v2pons/deploy/watch.sh'
#     sudo bash ~/v2pons/deploy/watch.sh
LOG="${1:-/var/log/flip/engine.jsonl}"
echo "watching $LOG (times UTC); a launch, our buy, our sell, the result. Ctrl-C to stop."
tail -n 0 -F "$LOG" 2>/dev/null | python3 -u -c '
import sys, json, time
for line in sys.stdin:
    try: e = json.loads(line)
    except Exception: continue
    t = time.strftime("%H:%M:%S", time.gmtime(e.get("t", 0))); ev = e.get("ev")
    if ev == "armed":
        print(t, "launch      fee %.4g%%, %s" % (e["fee"] / 1e4, "eligible" if e.get("eligible") else "not traded (fee or liquidity)"))
    elif ev == "fire":
        print(t, "BUY sent    trigger %.4f ETH, %s" % (e["trig_value"] / 1e18, "live" if not e.get("dry") else "dry"))
    elif ev == "would_fire":
        print(t, "would buy   (dry run)")
    elif ev == "buy_seen":
        print(t, "buy landed  %d blocks after the trigger" % e["offset"])
    elif ev in ("sell_sent", "would_sell"):
        print(t, "SELL sent   %s block(s) after our buy: %s" % (e.get("after_buy"), (e.get("why") or "").split(";")[0]))
    elif ev == "trade_done" and not e.get("dry"):
        r = e.get("ret"); pf = e.get("pulled_before_sell")
        print("\a" + t, "TRADE DONE  %s, $%+.3f; sold %s blocks after our buy, pull %s blocks after it%s" % (
            "return %+.1f%%" % (100 * r) if r is not None else "no fill", e.get("pnl_usd") or 0, e.get("sell_after_buy_blocks"),
            e.get("pull_after_buy_blocks"), "  PULL CAME FIRST" if pf else ""))
    elif ev == "skip":
        print(t, "skipped     " + str(e.get("why")))
    elif ev in ("alarm", "buy_rejected"):
        print("\a" + t, "ALARM       " + str(e.get("what") or e.get("reply"))[:240])
'
