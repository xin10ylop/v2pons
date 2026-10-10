import sys; sys.path.insert(0, "."); from h import *
reset(); E.state["nonce"] = 400; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(6000); p = front_launch(6005, 5)
print("S2 front pool status:", p["status"], "| last skip:", events("skip")[-1]["why"])
for s_ in range(6006, 6009): E.ingest(frame(s_, []))
print("S2 front pool status after FIRE_MAX:", p["status"], "| position:", E.state["position"])
E.ingest(frame(6045, [signed(CROWD, UR, TRIG, BUY_DATA, 90)]))
print("S2 the follow trigger it waited for:", events("skip")[-1]["why"], "| position:", E.state["position"])
