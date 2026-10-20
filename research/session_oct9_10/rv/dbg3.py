from harness import *
E.roll_day(); reset(); E.state["nonce"] = 100; E.state["trades_today"] = E.MAX_TRADES_PER_DAY
do_launch(1000)
E.ingest(frame(1031, [signed(CROWD, UR, TRIG, BUY_DATA, 1)]))
print([ (pid[:10], q.get("entry"), q["eligible"], q["status"], q["launch_seq"]) for pid, q in E.state["armed"].items()])
seq = 1040
print(any(q.get("entry") != "front" and q["eligible"] and q["status"] in ("armed", "delayed") and seq - q["launch_seq"] <= E.TRIGGER_MAX_BLOCKS for q in E.state["armed"].values()))
import inspect; src = inspect.getsource(E._fire if not hasattr(E, "_fire0") else E._fire); print(src[:200])
