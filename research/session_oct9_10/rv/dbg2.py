from harness import *
E.roll_day(); reset(); E.state["nonce"] = 100; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(1000)
E.ingest(frame(1031, [signed(CROWD, UR, TRIG, BUY_DATA, 1)]))
q = E.state["armed"][PID]
print({k: q[k] for k in ("status","eligible","launch_seq","entry","first_buy")}, E.state["arming"], E.DRY_RUN, E.FRONT_DRY_RUN, E.TRIGGER_MAX_BLOCKS)
LOGS_before = len(events())
front_launch(1040, 1)
for e in events()[LOGS_before:]: print({k: e[k] for k in e if k in ("ev","why","pid","seq","entry")})
