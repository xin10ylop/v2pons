exec(open(__file__.replace("probe_wedge.py", "probe_base.py")).read())
# A. a buy whose reply is lost and that never went in, the RPC down when settle re-reads the nonce: the engine nonce stays +2 for good
TRIG = int(0.04e18)
reset(); E.state["nonce"] = 170; NONCE_ON_CHAIN[0] = hex(170); p = do_launch(2500)
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}]
E.ingest(frame(2531, [signed(CROWD, UR, TRIG, BUY_DATA, 53)])); pos = E.state["position"]; assert pos and E.state["nonce"] == 172
REPLIES[:] = [{"error": {"message": "send failed twice: timed out"}}] * E.SELL_TRIES
E.RECEIPT_TIMEOUT_S = 0.3
_rpc = E.rpc
def down(method, params, tries=4, timeout=10):
    if method == "eth_getTransactionCount": raise RuntimeError("eth_getTransactionCount: <urlopen error [Errno -3] Temporary failure in name resolution>")
    return _rpc(method, params, tries, timeout)
E.rpc = down                                                    # the box's network still out when settle re-reads the nonce
for s_ in range(2532, 2538): E.ingest(frame(s_, []))
assert wait_for(lambda: [e for e in events("trade_done") if e.get("nonce") == 170], 4.0)
time.sleep(0.2); E.rpc = _rpc
print("after settle: engine nonce", E.state["nonce"], "chain", int(NONCE_ON_CHAIN[0], 16), "position", E.state["position"])
# the network is back; every later buy is refused 'nonce too high' (the sequencer's answer), and the refresh after it keeps the max
class Seq:
    def post(self, i, body, retry=True):
        raw = bytes.fromhex(json.loads(body)["params"][0][2:]); n = int.from_bytes(rlp.decode(raw)[0], "big"); SENT.append((i, raw))
        if n > int(NONCE_ON_CHAIN[0], 16): return {"error": {"code": -32000, "message": f"nonce too high: tx {n} state {int(NONCE_ON_CHAIN[0], 16)}"}}
        return {"result": "0x" + keccak(raw).hex()}
E.SENDER = Seq()
for k, base in enumerate((2600, 2700, 2800)):
    E.state["armed"].clear(); E.state["position"] = None; E.state["seq"] = base - 1
    p = do_launch(base); E.ingest(frame(base + 31, [signed(CROWD, UR, TRIG, BUY_DATA, 60 + k)]))
    time.sleep(0.1)
    print("launch", base, "position", E.state["position"] is not None, "last buy_rejected:", events("buy_rejected")[-1]["reply"]["error"]["message"][:40] if events("buy_rejected") else None, "engine nonce", E.state["nonce"])
