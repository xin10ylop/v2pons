"""Pull risk and the operator's reaction to outsiders on the v2.433 family (logs; 531 in-window + 102 forward pools).
outsider swap = a buy >= 1e-5 ETH whose PoolManager sender is not the Universal Router (sniper contracts 65050a9b, fd1b271f, ...), or a UR
buy that is not the bot's first buy and is < 0.01 ETH; the bot = UR buys >= 0.01 ETH."""
import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import hours
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
ps = sorted([p for p in P.values() if isf(p)] + [p for p in FP.values() if isf(p)], key=lambda p: p["b0"])
SP0 = 1604517591721945638372359205383840; L0 = 49279426163460954002188
pull_off = []; rel_bot = []; pre_big = []; room = []
after_out = collections.Counter(); base = collections.Counter()
for p in ps:
    b0 = p["b0"]; sw = p["sw"]
    pl = [m[0] for m in p["mls"] if m[4] < 0]; pull = pl[0] if pl else None
    bot = next((x for x in sw if x[2] < 0 and -x[2] >= 0.01e18), None)
    if pull is not None: pull_off.append(pull - b0)
    if pull is not None and bot is not None: rel_bot.append(pull - bot[0])
    if bot:
        pre = [x for x in sw if x[0] <= bot[0] and x is not bot and x[2] < 0 and (x[0], x[1]) < (bot[0], bot[1])]
        pre_eth = sum(-x[2] for x in pre)
        if any(-x[2] >= 0.0005e18 for x in pre): pre_big.append((p["pid"][:10], [(x[0] - b0, -x[2] / 1e18, x[6][:6]) for x in pre]))
        # room: extra ETH (gross) ahead of the bot buy that still leaves its output >= minOut (0.99 x launch quote)
        v = -bot[2]; mo = int(v4math.buy_out_int(SP0, L0, v, 2500) * 0.99)
        sp_pre = bot[4]  # placeholder
        prev = [x for x in sw if (x[0], x[1]) < (bot[0], bot[1])]; spb = prev[-1][4] if prev else SP0
        lo, hi = 0, int(0.05e18)
        while hi - lo > int(2e12):
            mid = (lo + hi) // 2
            s2 = v4math.sqrt_after_buy(spb, L0, mid - (mid * 2500 + 999999) // 10**6)
            if v4math.buy_out_int(int(s2), L0, v, 2500) >= mo: lo = mid
            else: hi = mid
        room.append(lo / 1e18)
    # reaction: for each outsider buy after the bot's first buy (and before the pull), is there a pull within 1..16 blocks? vs. every block
    if bot is None: continue
    outs = [x for x in sw if x[2] < 0 and -x[2] >= 1e13 and (x[0], x[1]) > (bot[0], bot[1]) and x[6] != UR and (pull is None or x[0] < pull)]
    for x in outs:
        after_out["n"] += 1
        if pull is not None and 1 <= pull - x[0] <= 16: after_out["pull<=16"] += 1
    # baseline: every block from bot+1 to min(pull, b0+300): P(pull in the next 16 blocks)
    end = min(pull if pull is not None else b0 + 3000, b0 + 3000)
    for b in range(bot[0] + 1, min(end, b0 + 300)):
        base["n"] += 1
        if pull is not None and 1 <= pull - b <= 16: base["pull<=16"] += 1
pull_off = np.array(pull_off); rel = np.array(rel_bot)
print("pools", len(ps), "pulled within 3000:", len(pull_off))
print("pull offset from launch: <= +8:", (pull_off <= 8).sum(), "<= +11:", (pull_off <= 11).sum(), "<= +13:", (pull_off <= 13).sum(), "<= +16:", (pull_off <= 16).sum(),
      "<= +23:", (pull_off <= 23).sum(), "<= +30:", (pull_off <= 30).sum())
print("pull - bot's first buy: <=1:", (rel <= 1).sum(), "<=2:", (rel <= 2).sum(), "<=3:", (rel <= 3).sum(), "<=5:", (rel <= 5).sum(), "<=10:", (rel <= 10).sum(), "min", rel.min())
print("pre-bot buys >= 0.0005 ETH:", len(pre_big), pre_big[:8])
room = np.array(room)
print("room before the bot's first buy reverts (ETH): p0/p1/p5/p50/p95", np.round(np.percentile(room, [0, 1, 5, 50, 95]), 5), " share < 0.012:", (room < 0.012).mean(), "< 0.0122:", (room < 0.0122).mean())
print("outsider buys after the bot's first buy:", after_out["n"], "followed by a pull within 1-16 blocks:", after_out["pull<=16"], f"({after_out['pull<=16']/max(1,after_out['n']):.3f})",
      "| baseline per block (bot+1..+300):", f"{base['pull<=16']/base['n']:.4f}")
