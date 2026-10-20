"""Calibration of the front pricer against the live record (HANDOFF 16.2: 405 relay trades Oct 10 09:08-11:39 UTC, $15 stake mean +14.1%
on the 315 priced): the replay on the v2.433 pools launched in that window (our real relay swaps removed, our trade re-inserted)."""
import sys, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import *
rows = [json.loads(l) for l in open(os.path.join(HERE, "pools_0.jsonl"))]
t0 = datetime.datetime(2026, 10, 10, 9, 8, tzinfo=datetime.timezone.utc).timestamp(); t1 = datetime.datetime(2026, 10, 10, 11, 40, tzinfo=datetime.timezone.utc).timestamp()
sel = [r for r in rows if t0 <= r["ts"] <= t1]
s = summarize([r["front"] for r in sel])
s_rel = summarize([r["front"] for r in sel if r.get("relay_buy_off") is not None])
print("v2.433 front, launches 09:08-11:40 UTC Oct 10:", json.dumps(s)); print("  of them with our real relay buy:", json.dumps(s_rel))
json.dump({"window": s, "with_relay": s_rel}, open(os.path.join(HERE, "calib_v2433_live.json"), "w"), indent=1)
