"""Independent front-room check on the BSC 12.4333285 line. For each pool (t22) with a bot first-buy through the router 0x07cb6161,
read that buy's BNB value X and its calldata minOut (word 4); price X at the pool's launch sqrtP with exact v4 integer math (fee 0.5%);
tolerance = minOut / quote. Then the room = the largest our-buy (full-range launch state) that still leaves the bot buy's output >= its
minOut, and our gain selling the tokens right after the bot's buy. Read-only; transactions from the 48 Club public BSC RPC."""
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail"); sys.path.insert(0, "/home/user/v2pons/src")
import xrpc, v4math
from common import jl, J, pct
R = "0x07cb61618b69234d954022ff738a015548715533"; FEE = 5000
def getbuys(rows):
    out = []
    for r in rows:
        sw = sorted(r["swaps"], key=lambda s: (s["b"], s["ix"]))
        fb = next((s for s in sw if s["to"] == R and s["a0"] < 0), None)
        if fb and abs(int(r["v"]) / 1e18 - 12.4333285) < 1e-6: out.append((r, fb))
    return out
rows = sorted({r["pid"]: r for r in jl(J("t22_pools_cache.jsonl"))}.values(), key=lambda r: r["L"])
pairs = getbuys(rows)
txc = {r["h"]: r for r in jl(J("t29_tx_cache.jsonl"))}
need = [fb["tx"] for _, fb in pairs if fb["tx"] not in txc]
with open(J("t29_tx_cache.jsonl"), "a") as f:
    for i in range(0, len(need), 10):
        for x in xrpc.batch("bsc", "eth_getTransactionByHash", [[h] for h in need[i:i + 10]], n=10):
            if x and x["input"][:10] == "0xc1120e3d":
                y = {"h": x["hash"], "mo": int(x["input"][10 + 64 * 4: 10 + 64 * 5], 16), "v": int(x["value"], 16)}
                txc[y["h"]] = y; f.write(json.dumps(y) + "\n")
tols = []; rooms = []; gains = []
for r, fb in pairs:
    t = txc.get(fb["tx"])
    if not t: continue
    sp = r["sqrtP"]; L = None
    # launch liquidity from the pool's first ModifyLiquidity (mls[0] is the mint)
    L = r["mls"][0]["dl"] if r["mls"] else None
    if not L or L < 0: continue
    X, mo = t["v"], t["mo"]
    quote = v4math.buy_out_int(sp, L, X, FEE)
    if quote <= 0: continue
    tol = mo / quote; tols.append(tol)
    # room: largest our-X such that bot buy (after our buy moves sp) still outputs >= mo
    lo, hi = 0, X * 4
    for _ in range(60):
        mid = (lo + hi) // 2
        our_out = v4math.buy_out_int(sp, L, mid, FEE); sp2 = int(v4math.sqrt_after_buy(sp, L, mid - (mid * FEE + 999999) // 1000000))
        bot_out = v4math.buy_out_int(sp2, L, X, FEE)
        if bot_out >= mo: lo = mid
        else: hi = mid
    room = lo; rooms.append(room / 1e18)
    # our gain: buy `room` BNB, sell the tokens after the bot's X buy
    our_tok = v4math.buy_out_int(sp, L, room, FEE); sp2 = int(v4math.sqrt_after_buy(sp, L, room - (room * FEE + 999999) // 1000000))
    sp3 = int(v4math.sqrt_after_buy(sp2, L, X - (X * FEE + 999999) // 1000000))
    back = v4math.sell_out_int(sp3, L, our_tok, FEE)
    if room > 0: gains.append((back - room) / room)
print("pools with a bot c1120e3d first buy on the 12.4333285 line:", len(tols))
print("bot first-buy tolerance minOut/quote p10/50/90:", [round(pct(tols, q), 4) for q in (.1, .5, .9)])
print("room ahead of the bot (BNB) p10/50/90:", [round(pct(rooms, q), 5) for q in (.1, .5, .9)], "median ~$", round(pct(rooms, .5) * 1200, 1))
print("our gain at that room, sell right after the bot p10/50/90:", [round(100 * pct(gains, q), 2) for q in (.1, .5, .9)], "% ; positive:", sum(1 for g in gains if g > 0), "of", len(gains))
