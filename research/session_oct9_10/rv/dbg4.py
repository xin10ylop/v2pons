from harness import *
import harness
E.roll_day(); reset(); E.state["nonce"] = 100; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(1000)
E.ingest(frame(1031, [signed(CROWD, UR, TRIG, BUY_DATA, 1)]))
orig = harness._fire0
def tr(p, seq, *a):
    print("in _fire", p["pid"][:10], "seq", seq, "armed:", [(q.get("entry"), q["status"], q["launch_seq"]) for q in E.state["armed"].values()], "dry", E.DRY_RUN, E.FRONT_DRY_RUN, "front", p.get("entry"))
    return orig(p, seq, *a)
harness._fire0 = tr
front_launch(1040, 1)
