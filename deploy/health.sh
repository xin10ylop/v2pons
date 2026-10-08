#!/bin/bash
# health.sh: the flip engine in one screen: the service, the start line, the last three hours' event counts, alarms, the open
# position, today's trades, the relay's money.    sudo bash ~/v2pons/deploy/health.sh
REPO="$(cd "$(dirname "$0")/.." && pwd)"
echo "flip-engine: $(systemctl is-active flip-engine 2>/dev/null)   feed/seq per start line:"
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
'
/opt/flip-venv/bin/python3 "$REPO/deploy/relay_ops.py" status 2>/dev/null || true
