
# ===================== repro scenarios (review06_nonce) =====================
done_at = lambda n: [e for e in events("trade_done") if e.get("nonce") == n]
net = lambda x: x - (x * 1134 + 999_999) // 1_000_000
TRIG = int(0.04e18)
E.DRY_RUN = False; E.RECEIPT_TIMEOUT_S = 0.3

RPC_DOWN = [False]
def flaky_rpc(method, params, tries=4, timeout=10):
    if RPC_DOWN[0] and method == "eth_getTransactionCount":
        raise RuntimeError("eth_getTransactionCount: HTTP Error 429: Too Many Requests")
    return fake_rpc(method, params, tries, timeout)
E.rpc = flaky_rpc
nonce_high = {"error": {"code": -32000, "message": "nonce too high"}}

# ---- A1: the buy's reply lost, the buy never went in, the one exact read fails
reset(); E.state["nonce"] = 170; NONCE_ON_CHAIN[0] = hex(170); p = do_launch(2500)
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}]
E.ingest(frame(2531, [signed(CROWD, UR, TRIG, BUY_DATA, 53)])); pos = E.state["position"]; assert pos and E.state["nonce"] == 172
REPLIES[:] = [nonce_high] * E.SELL_TRIES
RPC_DOWN[0] = True
for s_ in range(2532, 2538):
    E.ingest(frame(s_, []))
assert wait_for(lambda: done_at(170), 4.0); time.sleep(0.3)
RPC_DOWN[0] = False
print("A1 after settle: engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16), "position", E.state["position"], "halted", E.state["halted"])
# the next launch: the engine's buy goes at 172, the node says nonce too high
E.state["armed"].clear(); SENT.clear()
p = do_launch(2600)
REPLIES[:] = [nonce_high]
E.ingest(frame(2631, [signed(CROWD, UR, TRIG, BUY_DATA, 54)]))
time.sleep(0.3)
rj = events("buy_rejected")[-1]
print("A1 next buy: sent at nonce", int.from_bytes(rlp.decode(SENT[0][1])[0], "big"), "->", rj["reply"]["error"]["message"], "| engine nonce after its refresh:", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16))
# and one more, with the RPC fine now: still stuck
E.state["armed"].clear(); SENT.clear(); p = do_launch(2700); REPLIES[:] = [nonce_high]
E.ingest(frame(2731, [signed(CROWD, UR, TRIG, BUY_DATA, 55)])); time.sleep(0.3)
print("A1 third buy: sent at nonce", int.from_bytes(rlp.decode(SENT[0][1])[0], "big"), "| engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16))

# ---- A2: the buy lands and reverts (chain 301), the sell is never accepted (4 refusals), no RPC failure at all
reset(); E.state["nonce"] = 300; NONCE_ON_CHAIN[0] = hex(301); p = do_launch(3000)
E.ingest(frame(3031, [signed(CROWD, UR, TRIG, BUY_DATA, 60)])); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(3032, [])); E.ingest(frame(3033, [buy_raw]))
RECEIPTS["0x" + pos["buy_hash"]] = {"status": "0x0", "blockNumber": hex(3033), "gasUsed": hex(60000), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2", "logs": []}
REPLIES[:] = [{"error": {"message": "send failed twice: connection reset"}}] * E.SELL_TRIES
E.ingest(frame(3034, [])); E.ingest(frame(3035, []))
assert wait_for(lambda: done_at(300), 4.0); time.sleep(0.3)
d = done_at(300)[-1]
print("A2 after settle: buy", d["buy"]["status"], "sell", d["sell"], "| engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16), "halted", E.state["halted"])
print("nonce events:", [(e["chain"], e["engine"]) for e in events("nonce")][-6:])
