import sys; sys.path.insert(0, "."); from h import *
def run(name, setup):
    reset(); E.state["nonce"] = 400; E.state["relay_wei"] = None; setup()
    if name != "control-no-follow":
        do_launch(6000)
    p = front_launch(6005, 5)
    sk = [e["why"] for e in events("skip") if e.get("pid") == FPID][-1:] 
    fired = E.state["position"] is not None and E.state["position"]["pid"] == FPID
    for s_ in range(6006, 6009): E.ingest(frame(s_, []))
    st = p["status"] if p else None
    print(f"{name:22s} front fired={fired} front status={st} last front skip={sk}")
    if E.state["position"] is not None and E.state["position"]["pid"] == FPID:
        E.state["position"] = None
        return
    if name != "control-no-follow":
        E.ingest(frame(6045, [signed(CROWD, UR, TRIG, BUY_DATA, 90)]))
        last = events()[-1]
        print(f"{'':22s} follow trigger -> {last.get('ev')} {last.get('why','')} position={E.state['position'] is not None}")
    E.state["position"] = None
def cap(): E.state["trades_today"] = E.MAX_TRADES_PER_DAY
def stop(): E.state["pnl_today_usd"] = -E.DAILY_STOP_USD - 1
def relay(): E.state["relay_wei"] = E.STAKE_WEI - 1; E.FRONT_STAKE_WEI_SAVE = E.FRONT_STAKE_WEI
# relay below follow stake but at/above front stake: raise follow stake
E.STAKE_WEI_ORIG = E.STAKE_WEI
def relay2(): E.STAKE_WEI = int(0.0195e18); E.state["relay_wei"] = int(0.005e18)
which = sys.argv[1]
{"control-no-follow": lambda: run("control-no-follow", lambda: None), "follow-can-trade": lambda: run("follow-can-trade", lambda: None),
 "follow-at-cap": lambda: run("follow-at-cap", cap), "follow-at-daily-stop": lambda: run("follow-at-daily-stop", stop),
 "relay<follow stake": lambda: run("relay<follow stake", relay2)}[which]()
