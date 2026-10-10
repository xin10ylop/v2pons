from harness import *
reset(); E.state["nonce"] = 100; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(1000)
E.ingest(frame(1031, [signed(CROWD, UR, TRIG, BUY_DATA, 1)]))
for e in events(): print(e)
