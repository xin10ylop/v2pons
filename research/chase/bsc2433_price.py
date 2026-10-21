#!/usr/bin/env python3
"""bsc2433_price.py bsc2433.json [BOT_ROUTER]: the 2.433 operator's BNB pools (bsc2433_scan.py) and the early seat on them: the launch value
filter, the bot router's buys (a Swap whose `sender` is BOT_ROUTER, default 0x37dc44b6), the pull (a negative ModifyLiquidity); the seat
buys STAKE BNB at the end of launch+1 on the pool's virtual reserves (L, sqrtP from the last Swap or the launch) and sells after the bot's
1st / 3rd / 5th buy (the end of that block + 1), -100% when the pull is at or before the exit; fee 0.5% each way. And the reaction: pools with
another wallet's buy before the bot's first buy, against those without."""
import json, sys, collections, statistics as st
d = json.load(open(sys.argv[1])); BOT = (sys.argv[2] if len(sys.argv) > 2 else "0x37dc44b63a0a31058a72ab0b5e53e20a1716395e").lower()
Q = 2 ** 96; FEE = 0.005
def s128(h): v = int(h, 16); return v - (1 << 256) if v >> 255 else v
vals = collections.Counter(round(p["value"], 2) for p in d.values()); print("pools", len(d), "| launch values (top):", vals.most_common(6))
tgt = collections.Counter(p["to"][:10] for p in d.values()); print("launch targets:", tgt.most_common(4))
OP = {k: p for k, p in d.items() if 10.4 <= p["value"] <= 10.7}
print("operator-sized pools (10.4-10.7 BNB):", len(OP))
res = {k: collections.defaultdict(list) for k in (0.02, 0.05)}; react = collections.Counter(); first_bot = []; pulls = []
for pid, p in OP.items():
    N = p["bn"]; ev = sorted(p["ev"], key=lambda e: (e[0], e[1]))
    sqrtP, L = p["sqrtP0"], None; state = {}; bot = []; pull = None; early_other = False
    for b, li, kind, sender, data, txh in ev:
        w = [data[2 + 64 * i: 66 + 64 * i] for i in range(6)]
        if kind == "ml":
            delta = s128(w[2])
            if delta < 0 and pull is None and b > N: pull = b
            if delta > 0 and L is None: L = delta
            continue
        a0, a1 = s128(w[0]), s128(w[1]); sqrtP = int(w[2], 16); L = int(w[3], 16)
        state[b] = (sqrtP, L)
        buy = a0 < 0                                         # the swapper paid BNB (currency0)
        if buy and sender.lower() == BOT and (pull is None or b < pull): bot.append(b)
        elif buy and not bot and b > N and (pull is None or b < pull): early_other = True
    if pull: pulls.append(pull - N)
    react[("someone before the bot" if early_other else "nobody before the bot", "bot came" if bot else "bot never came")] += 1
    if not bot or L is None: continue
    first_bot.append(bot[0] - N)
    def at(b):
        ks = [k for k in state if k <= b]; return state[max(ks)] if ks else (p["sqrtP0"], L)
    for S in (0.02, 0.05):
        sp, l = at(N + 1); x = l / (sp / Q); y = l * (sp / Q)              # virtual reserves: BNB, tokens (wei units)
        dx = S * 1e18 * (1 - FEE); tok = y * dx / (x + dx)                    # our buy
        for k, name in ((1, "after the bot's 1st buy"), (3, "after its 3rd"), (5, "after its 5th")):
            if len(bot) < k: continue
            X = bot[k - 1] + 1
            if pull is not None and pull <= X: res[S][name].append(-1.0); continue
            sp2, l2 = at(X); x2 = l2 / (sp2 / Q); y2 = l2 * (sp2 / Q)
            x2 += dx; y2 -= tok                                               # our own buy still in the pool
            out = x2 * tok / (y2 + tok) * (1 - FEE); res[S][name].append(out / (S * 1e18) - 1)
print("bot's first buy, blocks after launch: median", st.median(first_bot) if first_bot else None, "| p10/p90", sorted(first_bot)[len(first_bot) // 10] if first_bot else None, sorted(first_bot)[len(first_bot) * 9 // 10] if first_bot else None)
print("pull, blocks after launch: median", st.median(pulls) if pulls else None, "(%.1f min)" % (st.median(pulls) * 0.45 / 60) if pulls else "")
print("reaction:", dict(react))
for S, r in res.items():
    for name, v in r.items():
        print("stake %.2f BNB, sold %s: n=%d mean %+.1f%% median %+.1f%% won %d pulled %d | %+.4f BNB a pool" % (S, name, len(v), 100 * st.mean(v), 100 * st.median(v), sum(x > 0 for x in v), sum(x == -1 for x in v), S * st.mean(v)))
