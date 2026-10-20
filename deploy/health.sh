#!/bin/bash
# health.sh: the flip engine in one screen: the service, the start line, the last three hours' event counts, alarms, the open
# position, today's trades, the relay's money.    sudo bash ~/v2pons/deploy/health.sh
REPO="$(cd "$(dirname "$0")/.." && pwd)"
echo "flip-engine: $(systemctl is-active flip-engine 2>/dev/null)   feed/seq per start line:"
[ -f /var/log/flip/HALTED ] && echo "HALTED (live trading stopped until the file is removed): $(cat /var/log/flip/HALTED)"
python3 "$REPO/deploy/englog.py" 24 | grep '"ev":"start"' | tail -1 | cut -c1-300
echo "--- last 3 h"
python3 "$REPO/deploy/englog.py" 3 | python3 -c '
import sys, json, collections
c = collections.Counter(); last = {}
for l in sys.stdin:
    try: e = json.loads(l)
    except Exception: continue
    c[e["ev"]] += 1; last[e["ev"]] = e
print("events:", dict(c.most_common()))
for ev in ("alarm", "feed_error", "feed_stall", "buy_rejected"):
    if ev in last: print(ev + ":", json.dumps(last[ev])[:300])
for ev in ("armed", "first_buy", "would_fire", "fire", "trade_done"):
    if ev in last: print("last " + ev + ":", json.dumps(last[ev])[:300])
d = last.get("trade_done")
if d and not d.get("dry"):                                   # the fields that decided every live trade, whatever the line length
    print("last trade:", {k: d.get(k) for k in ("ret", "pnl_usd", "sell_why", "tp_ret", "buy_offset", "sell_after_buy_blocks", "pull_after_buy_blocks", "pulled_before_sell")})
'
/opt/flip-venv/bin/python3 "$REPO/deploy/relay_ops.py" status 2>/dev/null || true
if [ -f /var/log/flip/bnb.jsonl ]; then                      # the BNB line (flip-bnb): its trouble only, nothing when all is well
    echo "flip-bnb: $(systemctl is-active flip-bnb 2>/dev/null)"
    python3 "$REPO/deploy/bnb_results.py" --alerts
fi
if [ -f /var/log/flip/base_v2.jsonl ]; then                  # the Base V2 line (flip-base-v2): its trouble only, nothing when all is well
    echo "flip-base-v2: $(systemctl is-active flip-base-v2 2>/dev/null)"
    python3 "$REPO/deploy/base_v2_results.py" --alerts
fi
