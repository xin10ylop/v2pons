import sys, os
TEST = "/home/user/v2pons/tests/test_engine.py"
src = open(TEST).read(); src = src[:src.rindex("os.remove(LOG)")]
g = {"__name__": "__main__", "__file__": TEST}
exec(compile(src, TEST, "exec"), g); globals().update(g)
print("==== money scenarios")
E.FRONT = True; E.ENTRY = "auto"; E.MAX_TRADES_PER_DAY = 50; E.FRONT_MAX_PER_DAY = 50
for f_ in (E.HALT_FILE, E.FRONT_HALT_FILE):
    if os.path.exists(f_): os.remove(f_)
E.state["halted"] = None; E.state["front_halted"] = None

def pulled_front(seq0, nonce0, stake_wei):
    E.FRONT_STAKE_WEI = stake_wei
    reset(); E.state["nonce"] = nonce0; p = front_launch(seq0, nonce0 % 1000 + 100); pos = E.state["position"]; buy_raw = SENT[0][1]
    E.ingest(frame(seq0 + 1, [buy_raw]))
    for s_ in range(seq0 + 2, seq0 + 14): E.ingest(frame(s_, []))
    assert pos["sell_sent"], pos
    LOGS[:] = [{"blockNumber": hex(seq0 + 6), "transactionIndex": hex(1), "data": "0x" + w(-887250) + w(887250) + w(-FX["liq"]) + w(0)}]
    RECEIPTS["0x" + pos["buy_hash"]] = swap_receipt(seq0 + 1, -stake_wei, pos["feed_tokens"], pid=FPID)
    RECEIPTS["0x" + pos["sell_hash"]] = {"status": "0x1", "blockNumber": hex(seq0 + 15), "gasUsed": hex(135200), "effectiveGasPrice": hex(20_000_000), "transactionIndex": "0x2",
                                         "logs": [{"address": PM, "topics": ["0x" + E.T_SWAP, FPID, "0x" + w(RELAY)], "data": "0x" + w(0) + w(0) + w(1) + w(1) + w(0) + w(0)}]}
    assert wait_for(lambda: done_at(nonce0), 8)
    LOGS[:] = []

# S1 shared daily stop: one pulled front trade at the allowed max stake (0.006) stops the live follow strategy for the day
E.FRONT_DRY_RUN = False
pulled_front(7000, 500, int(0.006e18))
print("S1 front_halted:", bool(E.state["front_halted"]), "global halted:", E.state["halted"], "pnl_today_usd:", E.state["pnl_today_usd"])
pnl = E.state["pnl_today_usd"]
E.state["armed"].clear(); E.state["position"] = None; SENT.clear(); E.state["seq"] = 0; E.state["nonce"] = 510
p = do_launch(7100); E.state["pnl_today_usd"] = pnl
E.ingest(frame(7131, [signed(CROWD, UR, TRIG, BUY_DATA, 120)]))
print("S1 follow after one front pull: position", E.state["position"] is not None, "| skip:", events("skip")[-1].get("why"))
os.remove(E.FRONT_HALT_FILE); E.state["front_halted"] = None; E.FRONT_STAKE_WEI = int(0.0012e18); E.state["pnl_today_usd"] = 0.0

# S2 a front-shaped tx with sqrtPriceX96 = 0 ahead of a follow trigger in the same block
reset(); E.state["nonce"] = 520; E.FRONT_DRY_RUN = True
p = do_launch(7200)
b = bytearray(bytes.fromhex(FX["input"][2:])); arr = 4 + E._u(b, 4); st, ln = E._dyn(b, arr + 32, arr + 32); k = st + 4
b[k + 160:k + 192] = b"\x00" * 32
poison = signed(OUTSIDER, POSM, E.FRONT_VALUE_WEI, "0x" + b.hex(), 60)
try:
    E.ingest(frame(7231, [poison, signed(CROWD, UR, TRIG, BUY_DATA, 121)])); print("S2 no exception")
except Exception as ex:
    print("S2 ingest raised:", type(ex).__name__, ex)
print("S2 follow pool first_buy", p["first_buy"], "status", p["status"], "position", E.state["position"] is not None)
E.ingest(frame(7240, [signed(CROWD, UR, TRIG, BUY_DATA, 122)]))
pos = E.state["position"]
print("S2 the crowd's NEXT buy (+40) fires as the trigger:", pos is not None and pos["trig_seq"], "launch 7200")
E.state["position"] = None

# S3 a live front position open when a follow pool's first buy comes: the follow pool is lost for good
E.FRONT_DRY_RUN = False
reset(); E.state["nonce"] = 530
p = do_launch(7290)
fp = front_launch(7300, 61); fpos = E.state["position"]; assert fpos and not fpos["dry"]
E.ingest(frame(7320, [signed(CROWD, UR, TRIG, BUY_DATA, 123)]))
print("S3 follow pool status", p["status"], "first_buy", p["first_buy"], "skip:", events("skip")[-1].get("why"))
E.state["position"] = None
E.ingest(frame(7325, [signed(CROWD, UR, TRIG, BUY_DATA, 124)]))
print("S3 after the front position closed, the follow pool's next crowd buy -> position:", E.state["position"])

# S4 FRONT_STAKE_ETH=0 (operator 'turning the stake off'): the buy goes at the follow stake with minOut 0
E.FRONT_STAKE_WEI = 0; E.STAKE_WEI = int(0.0195e18)
reset(); E.state["nonce"] = 540; fp = front_launch(7400, 62); pos = E.state["position"]
bf = rlp.decode(SENT[0][1]); data = bf[5].hex()[8:]
amt = int(data[64*5:64*6], 16); mo = int(data[64*6:64*7], 16)
print("S4 pos.stake", pos["stake"], "tx amountIn", amt / 1e18, "ETH, minOut", mo)
E.state["position"] = None; E.FRONT_STAKE_WEI = int(0.0012e18); E.STAKE_WEI = int(0.0012e18)

# S5 phantom TP: 0.011 ETH bought behind ours (bot's buy now reverts per the bot's ~1% quote); the bot's 0.12 ETH buy still prices a TP
reset(); E.state["nonce"] = 550; fp = front_launch(7500, 63); pos = E.state["position"]; buy_raw = SENT[0][1]
E.ingest(frame(7501, [buy_raw, signed(OUTSIDER, "0x" + "65" * 20, int(0.011e18), FBUY, 64)]))
print("S5 after a 0.011 ETH buy behind ours: sell_sent", pos["sell_sent"])
sp_before = fp["sp"]
E.ingest(frame(7509, [signed(CROWD, BOT, int(0.12e18), FBUY, 125)]))
print("S5 the bot's buy (ETH ahead of it: 0.0122) -> sell_why", pos.get("sell_why"), "tp_ret", pos["tp_ret"], "engine price moved x", round((fp["sp"] / sp_before) ** 2, 4))
E.state["position"] = None
print("==== done")
os.remove(LOG)
