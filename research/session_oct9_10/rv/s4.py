import sys; sys.path.insert(0, "."); from h import *
import threading as T
reset(); E.state["nonce"] = 300
RealThread = E.threading.Thread
class FailOnce(RealThread):
    n = [0]
    def start(self):
        if getattr(self, "_target", None) is E.arm_launch_thread and FailOnce.n[0] == 0:
            FailOnce.n[0] += 1; raise RuntimeError("can't start new thread")
        return RealThread.start(self)
E.threading.Thread = FailOnce
raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), 0); E.ingest(frame(4000, [raw]))
E.threading.Thread = RealThread
print("arming after a failed thread start:", E.state["arming"])
for k in range(5):                                                       # front launches long after, no follow pool waiting
    p = front_launch(9000 + 1000 * k, 10 + k)
    for s_ in range(9001 + 1000 * k, 9004 + 1000 * k): E.ingest(frame(s_, []))
    print("front launch", k, "status", p["status"], "| skip:", [e["why"] for e in events("skip") if e.get("pid") == FPID][-2:]); E.state["armed"].pop(FPID)
