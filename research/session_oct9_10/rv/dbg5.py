from harness import *
import harness
E.roll_day(); reset(); E.state["nonce"] = 100; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(1000)
E.ingest(frame(1031, [signed(CROWD, UR, TRIG, BUY_DATA, 1)]))
orig = harness._fire0
def tr(p, seq, *a):
    st = E.state
    front = p.get("entry") == "front"; dry = E.DRY_RUN or (front and E.FRONT_DRY_RUN)
    print("halted", st["halted"], st["front_halted"], "pos", st["position"] is not None, "cap", st["front_today"], "pnl", st["front_pnl_today_usd"], "relay", st["relay_wei"])
    print("prio", front and not dry and (st["arming"] or any(q.get("entry") != "front" and q["eligible"] and q["status"] in ("armed", "delayed") and seq - q["launch_seq"] <= E.TRIGGER_MAX_BLOCKS for q in st["armed"].values())))
    n0 = len(events())
    r = orig(p, seq, *a)
    for e in events()[n0:]: print("  ", e.get("ev"), e.get("why"))
    return r
harness._fire0 = tr
front_launch(1040, 1)
