import os, sys
ROOT = "/home/user/v2pons"
src = open(os.path.join(ROOT, "tests", "test_engine.py")).read().split("# 17c.")[0]
g = {"__file__": os.path.join(ROOT, "tests", "test_engine.py"), "__name__": "__main__"}
exec(compile(src, "test_engine_head", "exec"), g)
E = g["E"]; reset = g["reset"]; signed = g["signed"]; frame = g["frame"]; FX = g["FX"]; POSM = g["POSM"]; DEPLOYER = g["DEPLOYER"]; OUTSIDER = g["OUTSIDER"]; FBUY = g["FBUY"]; SENT = g["SENT"]; FPID = g["FPID"]; events = g["events"]
# scenario: a sniper buys 0.0005 ETH in the launch block after the launch tx
reset(); E.state["nonce"] = 400
launch = signed(DEPLOYER, POSM, E.FRONT_VALUE_WEI, FX["input"], 3)
snipe = signed(OUTSIDER, "0x" + "65" * 20, int(0.0005e18), FBUY, 31)
E.ingest(frame(6000, [launch, snipe]))
p = E.state["armed"].get(FPID)
print("status", p["status"], "first_buy", p["first_buy"], "position", E.state["position"], "sent", len(SENT))
for s in range(6001, 6004):
    E.ingest(frame(s, []))
print("after L+3: status", p["status"], "position", E.state["position"], "sent", len(SENT))
print([e for e in events() if e.get("pid") == FPID][-3:])
