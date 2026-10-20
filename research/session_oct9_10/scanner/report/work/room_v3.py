# The room ahead of the v3.0 bot's buy: the ETH that can be bought ahead of it (at the launch state) before its buy fails a minOut of
# 0.95 (today) or 0.99 (v2.433's) of the launch-state quote, for bot buys of 0.0495, 0.124 and 0.236 ETH (min, median, max). Output room_v3.json.
import sys, json; sys.path.insert(0, "/home/user/v2pons/src")
import v4math
SP = 679394651928963067279918579724198; L = 25725498245903809899643; FEE = 10000
def net(x): return x - (x * FEE + 999_999) // 1_000_000
def room(Y, ratio):
    q0 = v4math.buy_out_int(SP, L, Y, FEE); lo, hi = 0, int(1e18)
    while hi - lo > int(1e12):
        m = (lo + hi) // 2
        if v4math.buy_out_int(int(v4math.sqrt_after_buy(SP, L, net(m))), L, Y, FEE) >= ratio * q0: lo = m
        else: hi = m
    return round(lo / 1e18, 4)
out = {str(Y): {"minout_0.95": room(int(Y * 1e18), 0.95), "minout_0.99": room(int(Y * 1e18), 0.99)} for Y in (0.0495, 0.124, 0.236)}
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/room_v3.json", "w"), indent=1); print(out)
