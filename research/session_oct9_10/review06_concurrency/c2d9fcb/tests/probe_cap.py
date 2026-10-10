exec(open(__file__.replace("probe_cap.py", "probe_base.py")).read())
TRIG = int(0.04e18); E.MAX_TRADES_PER_DAY = 1                       # the runbook's "live, one trade first"
reset(); E.state["nonce"] = 170; NONCE_ON_CHAIN[0] = hex(170); p = do_launch(2500)
REPLIES[:] = [{"error": {"message": "send failed twice: [Errno 104] Connection reset by peer"}}]   # the buy never reached the sequencer
E.ingest(frame(2531, [signed(CROWD, UR, TRIG, BUY_DATA, 53)])); pos = E.state["position"]
REPLIES[:] = [{"error": {"code": -32000, "message": "nonce too high"}}] * E.SELL_TRIES; E.RECEIPT_TIMEOUT_S = 0.3
for s_ in range(2532, 2538): E.ingest(frame(s_, []))
assert wait_for(lambda: E.state["position"] is None and E.state["nonce"] == 170, 4.0)
d = [e for e in events("trade_done") if e.get("nonce") == 170][-1]
print("trade_done buy:", d["buy"], "sell:", d["sell"], "pnl_usd", d["pnl_usd"], "trades_today", E.state["trades_today"])
E.state["armed"].clear(); p = do_launch(2600); E.ingest(frame(2631, [signed(CROWD, UR, TRIG, BUY_DATA, 54)]))
print("next launch:", events("skip")[-1]["why"], "position", E.state["position"])
