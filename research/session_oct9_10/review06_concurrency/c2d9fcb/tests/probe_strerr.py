exec(open(__file__.replace("probe_strerr.py", "probe_base.py")).read())
TRIG = int(0.04e18)
reset(); E.state["nonce"] = 300; p = do_launch(3000)
E.ingest(frame(3031, [signed(CROWD, UR, TRIG, BUY_DATA, 70)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(3032, [])); E.ingest(frame(3033, [buy_raw])); E.ingest(frame(3034, []))
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(3033, -E.STAKE_WEI, pos["feed_tokens"])
REPLIES[:] = [{"jsonrpc": "2.0", "id": 1, "error": "Too Many Requests"}]       # a gateway's rate limit, error as a string
E.ingest(frame(3035, []))                                                      # the deadline: the sell goes to deliver_sell
time.sleep(1.5)
print("sell_sent flag", pos["sell_sent"], "sell posts", sum(1 for i, r in SENT if r == pos["sell_raw"]), "sell_sent events", len(events("sell_sent")), "trade_done", len(events("trade_done")))
print("position still open:", E.state["position"] is pos)
p2 = dict(p, pid="0x" + "88" * 32, token="cd" * 20, token_bytes=bytes.fromhex("cd" * 20), first_buy=None, status="armed", launch_seq=3100); E.state["armed"][p2["pid"]] = p2
E.ingest(frame(3131, [signed(CROWD, UR, TRIG, "0x24856bc3" + w("0x" + "cd" * 20), 71)]))
print("next launch:", events("skip")[-1]["why"] if events("skip") else None)
