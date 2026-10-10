import sys; sys.path.insert(0, "."); from h import *
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
print("alarms:", [(e.get("what"), e.get("trace","")[-60:]) for e in events("alarm")])
print("armed follow pools:", [p for p in E.state["armed"]])
# dry front: unaffected?
E.FRONT_DRY_RUN = True
p = front_launch(9000, 10)
for s_ in range(9001, 9004): E.ingest(frame(s_, []))
print("dry front status", p["status"], "would_fire:", len([e for e in events("would_fire") if e.get("pid") == FPID]))
