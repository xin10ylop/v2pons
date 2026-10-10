import sys, os
src = open("/home/user/v2pons/tests/test_engine.py").read()
src = src[:src.rindex("os.remove(LOG)")]
import builtins
g = {"__name__": "__main__", "__file__": "/home/user/v2pons/tests/test_engine.py"}
exec(compile(src, "/home/user/v2pons/tests/test_engine.py", "exec"), g)
globals().update(g)
print("==== scenarios")
import json as _j
E.FRONT = True; E.ENTRY = "auto"; E.MAX_TRADES_PER_DAY = 50; E.FRONT_MAX_PER_DAY = 50
for f_ in (E.HALT_FILE, E.FRONT_HALT_FILE):
    if os.path.exists(f_): os.remove(f_)
E.state["halted"] = None; E.state["front_halted"] = None

# A: shared daily stop: a front pull at FRONT_STAKE 0.006 stops follow
E.FRONT_DRY_RUN = False; E.FRONT_STAKE_WEI = int(0.006e18)
reset(); E.state["nonce"] = 400; p = front_launch(6000, 5); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(6001, [buy_raw]))
for s_ in range(6002, 6013): E.ingest(frame(s_, []))
E.ingest(frame(6013, [])); assert pos["sell_sent"], pos
LOGS[:] = [{"blockNumber": hex(6006), "transactionIndex": hex(1), "data": "0x" + w(-887250) + w(887250) + w(-FX["liq"]) + w(0)}]
RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(6001, -E.FRONT_STAKE_WEI, pos["feed_tokens"], pid=FPID)
RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x1", "blockNumber": hex(6014), "gasUsed": hex(135200), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2",
                                     "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, FPID, "0x" + w(RELAY)], "data": "0x" + w(1) + w(0) + w(1) + w(1) + w(0) + w(0)}]}
assert wait_for(lambda: done_at(400))
print("A: front_halted", bool(E.state["front_halted"]), "halted", E.state["halted"], "pnl_today", E.state["pnl_today_usd"])
LOGS[:] = []
E.state["armed"].clear(); E.state["position"] = None; SENT.clear(); E.state["seq"] = 0; E.state["nonce"] = 410
p = do_launch(6100); E.ingest(frame(6131, [signed(CROWD, UR, TRIG, BUY_DATA, 90)]))
print("A: follow position after a front pull:", E.state["position"], "| last skip:", events("skip")[-1].get("why"))
os.remove(E.FRONT_HALT_FILE); E.state["front_halted"] = None; E.FRONT_STAKE_WEI = int(0.0012e18)

# B: a front-shaped tx with sqrtPriceX96 = 0 in the same block as a follow trigger
reset(); E.state["nonce"] = 420; E.FRONT_DRY_RUN = True
p = do_launch(6200)
b = bytearray(bytes.fromhex(FX["input"][2:])); d0 = E.decode_launch(bytes(b))
# find the init call's sqrt word: locate the packed key then +160
kb_hex = None
import re
arr = 4 + E._u(b, 4); st, ln = E._dyn(b, arr + 32, arr + 32)
k = st + 4; assert E._u(b, k + 160) == d0["sqrt_p"]; b[k + 160:k + 192] = b"\x00" * 32
poison = signed(OUTSIDER, POSM, E.FRONT_VALUE_WEI, "0x" + b.hex(), 50)
trig = signed(CROWD, UR, TRIG, BUY_DATA, 91)
try:
    E.ingest(frame(6231, [poison, trig])); print("B: no exception")
except Exception as ex:
    print("B: ingest raised", type(ex).__name__, ex)
print("B: follow pool first_buy", p["first_buy"], "position", E.state["position"] is not None, "state.seq", E.state["seq"])
E.ingest(frame(6231, [trig])); print("B: replaying the block is ignored (seq <= state.seq): position", E.state["position"] is not None)

# C: a live front position open when the follow pool's first buy comes: the follow pool is lost for good
E.FRONT_DRY_RUN = False
reset(); E.state["nonce"] = 430; E.state["seq"] = 0
p = do_launch(6290)
fp = front_launch(6300, 6); fpos = E.state["position"]; assert fpos and not fpos["dry"]
E.ingest(frame(6320, [signed(CROWD, UR, TRIG, BUY_DATA, 92)]))
print("C: follow pool status", p["status"], "first_buy", p["first_buy"], "skip:", events("skip")[-1].get("why"))
E.state["position"] = None
E.ingest(frame(6325, [signed(CROWD, UR, TRIG, BUY_DATA, 93)]))
print("C: after the front closed, the follow pool's next buy: position", E.state["position"])
os.remove(LOG)
