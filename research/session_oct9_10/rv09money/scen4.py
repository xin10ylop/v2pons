import sys, os, threading, time as _t
TEST = "/home/user/v2pons/tests/test_engine.py"
src = open(TEST).read(); src = src[:src.rindex("os.remove(LOG)")]
g = {"__name__": "__main__", "__file__": TEST}
exec(compile(src, TEST, "exec"), g); globals().update(g)
print("==== watchdog stale read across a dry-front drop")
E.FRONT = True; E.FRONT_DRY_RUN = True; E.ENTRY = "auto"
for f_ in (E.HALT_FILE, E.FRONT_HALT_FILE):
    if os.path.exists(f_): os.remove(f_)
E.state["halted"] = None; E.state["front_halted"] = None
reset(); E.state["nonce"] = 800
fp = front_launch(9500, 95); fpos = E.state["position"]; assert fpos["dry"]
E.state["armed"].pop(FPID, None)
p = do_launch(9600); E.state["position"] = fpos
fpos["fired_at"] -= fpos["fallback_s"] + 1.0                                   # the dry front position is past its time fallback, sell not sent
E.lock.acquire()                                          # the feed thread is inside ingest (holds the lock) when the watchdog ticks
t = threading.Thread(target=E.watchdog_tick); t.start(); _t.sleep(0.2)   # the watchdog read the dry position and waits for the lock
E.ingest(frame(9631, [signed(CROWD, UR, TRIG, BUY_DATA, 150)]))          # same thread: the follow trigger drops the dry front and fires live
pos = E.state["position"]; assert pos is not fpos and not pos["dry"]
E.lock.release(); t.join()
print("live follow pos sell_sent:", pos["sell_sent"], "why:", pos.get("sell_why"), "buy_seq:", pos["buy_seq"], "sends:", len(SENT))
_t.sleep(0.5)
os.remove(LOG)
