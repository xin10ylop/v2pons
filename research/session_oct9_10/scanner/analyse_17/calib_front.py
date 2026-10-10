"""v2.433 front control split: by the bot's first-buy size, and over the live window of Oct 10 09:07-11:40 UTC (HANDOFF 16.2: +14.1% on 315 $15 trades)."""
import sys, os, json, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common17 import summarize, fmt_rule
R = json.load(open(os.path.join(HERE, "rows.json")))["rows"]["control:vbot-v2.433"]
out = {}
big = [r["front"] for r in R if r["sched"] and r["sched"]["eth"] >= 0.04 and r["front"].get("trig") is not None and r["front"]["trig"] <= 19]
small = [r["front"] for r in R if r["sched"] and r["sched"]["eth"] < 0.04 and r["front"].get("trig") is not None and r["front"]["trig"] <= 19]
import datetime
t0 = datetime.datetime(2026, 10, 10, 9, 7, tzinfo=datetime.timezone.utc).timestamp(); t1 = datetime.datetime(2026, 10, 10, 11, 40, tzinfo=datetime.timezone.utc).timestamp()
live = [r["front"] for r in R if t0 <= r["ts"] <= t1]
for name, xs in (("bot_buy_ge_0.04_by_+19", big), ("bot_buy_lt_0.04_by_+19", small), ("launched_Oct10_09:07-11:40", live)):
    s = summarize(xs); out[name] = s; print(name, fmt_rule(s))
json.dump(out, open(os.path.join(HERE, "calib_front.json"), "w"), indent=1)
