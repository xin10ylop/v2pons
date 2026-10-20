import sys, os
TEST = "/home/user/v2pons/tests/test_engine.py"
src = open(TEST).read(); src = src[:src.rindex("os.remove(LOG)")]
g = {"__name__": "__main__", "__file__": TEST}
exec(compile(src, TEST, "exec"), g); globals().update(g)
print("==== liq-0 lookalike")
E.FRONT = True; E.FRONT_DRY_RUN = True; E.ENTRY = "auto"
for f_ in (E.HALT_FILE, E.FRONT_HALT_FILE):
    if os.path.exists(f_): os.remove(f_)
E.state["halted"] = None; E.state["front_halted"] = None
b = bytearray(bytes.fromhex(FX["input"][2:]))
d0 = E.decode_launch(bytes(b))
# find the MINT_POSITION params: locate the second copy of the 160-byte key
arr = 4 + E._u(b, 4); st, ln = E._dyn(b, arr + 32, arr + 32); key = bytes(b[st + 4: st + 164])
j = bytes(b).find(key, st + 164); assert j > 0
b[j + 160:j + 192] = (887200).to_bytes(32, "big")                   # tickLower above the price: the mint is out of range
d1 = E.decode_launch(bytes(b)); print("decoded lo/hi", d1["lo"], d1["hi"], "tick0", E.tick_at(d1["sqrt_p"]))
reset(); E.state["nonce"] = 600
E.ingest(frame(8000, [signed(OUTSIDER, POSM, E.FRONT_VALUE_WEI, "0x" + b.hex(), 80)]))
fp = E.state["armed"].get(FPID); print("armed liq", fp["liq"], "eligible", fp["eligible"], "status", fp["status"])
p = do_launch(8010)   # a live follow pool, armed after it
errs = 0
for i, s_ in enumerate(range(8020, 8025)):
    try:
        E.ingest(frame(s_, [signed(CROWD, BOT, int(0.001e18), FBUY, 130 + i), signed(CROWD, UR, TRIG, BUY_DATA, 140 + i)]))
    except Exception as ex:
        errs += 1; last = ex
print("blocks whose ingest raised:", errs, type(last).__name__, last, "| follow first_buy:", p["first_buy"], "position:", E.state["position"] is not None)
os.remove(LOG)
