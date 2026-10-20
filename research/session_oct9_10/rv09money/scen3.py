import sys, os
TEST = "/home/user/v2pons/tests/test_engine.py"
src = open(TEST).read(); src = src[:src.rindex("os.remove(LOG)")]
g = {"__name__": "__main__", "__file__": TEST}
exec(compile(src, TEST, "exec"), g); globals().update(g)
print("==== lookalike with a fake price, any sender, other fee")
E.FRONT = True; E.FRONT_DRY_RUN = False; E.ENTRY = "auto"; E.FRONT_MAX_PER_DAY = 50
for f_ in (E.HALT_FILE, E.FRONT_HALT_FILE):
    if os.path.exists(f_): os.remove(f_)
E.state["halted"] = None; E.state["front_halted"] = None
b = bytearray(bytes.fromhex(FX["input"][2:]))
arr = 4 + E._u(b, 4); st, ln = E._dyn(b, arr + 32, arr + 32); k = st + 4; key = bytes(b[k:k + 160])
j = bytes(b).find(key, k + 160); assert j > 0
real = E.decode_launch(bytes(b))
b[k + 160:k + 192] = (1 << 96).to_bytes(32, "big")                 # a fake initial price (the init would revert on an existing pool: the feed still shows it)
for off in (k, j):                                                  # fee 2500 -> 9000 in both copies of the key
    b[off + 64:off + 96] = (9000).to_bytes(32, "big")
d = E.decode_launch(bytes(b)); print("decoded fee", d["fee"], "ts", d["tick_spacing"], "sqrt_p", d["sqrt_p"], "pid", d["pid"][:12])
reset(); E.state["nonce"] = 700
E.ingest(frame(9000, [signed(OUTSIDER, POSM, E.FRONT_VALUE_WEI, "0x" + b.hex(), 90)]))
pos = E.state["position"]
real_tokens = v4math.buy_out_int(real["sqrt_p"], real["mint_liq"], E.FRONT_STAKE_WEI, 2500)
print("fired:", pos is not None, "from a sender that is not the bot; min_out", pos and pos["min_out"], "vs tokens at a real launch price", real_tokens)
E.state["position"] = None
os.remove(LOG)
