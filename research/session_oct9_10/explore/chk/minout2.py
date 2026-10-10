"""v2.433: the volume bot's router buys (c1120e3d): minOut (word 4) vs the tokens it got, and vs the exact quote at each earlier state:
which state did its quote see? How much headroom does a buy of ours at +3 leave it?"""
import pickle, sys, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb")); TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
FEE = 2500
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
first_ratio = []; all_ratio = []; lagseen = collections.Counter(); headroom = {0.0012e18: [], 0.012e18: []}; w3r = []
nomatch = 0; firsts = 0
for p in fam:
    states = [(p["b0"], p["sp0"], p["sw"][0][5])]   # (block, sp, L) after each swap
    nb = 0
    for x in p["sw"]:
        bn = x[0]; t = TX.get(x[7])
        if t and t["sel"] == "0xc1120e3d" and x[2] < 0:
            mo = wd(t["input"], 4); X = t["value"]; got = x[3]
            r = mo / got; all_ratio.append(r)
            if nb == 0:
                first_ratio.append(r); firsts += 1
                w3r.append(wd(t["input"], 3) / got)
                # quote state: the latest state k whose exact quote q_k satisfies mo/q_k == the family constant
                qs = [(k, mo / v4math.buy_out_int(sp, L, X, FEE)) for k, (b, sp, L) in enumerate(states)]
                # our buy inserted right after the launch state (before everything else up to the bot's buy): the bot's output
                sp, L = states[-1][1], states[-1][2]
                for S in headroom:
                    # state after all earlier swaps plus ours (1/sqrtP additive for buys)
                    sp_us = v4math.sqrt_after_buy(sp, L, S - (S * FEE + 999999) // 1000000)
                    out_us = v4math.buy_out_int(int(sp_us), L, X, FEE)
                    headroom[S].append((out_us / got, mo / got, out_us >= mo))
            nb += 1
        states.append((bn, x[4], x[5]))
def q(v, qs=(0, .01, .05, .1, .25, .5, .75, .9, 1)):
    v = sorted(v); return [round(v[int(a * (len(v) - 1))], 6) for a in qs]
print("first bot buys", firsts, "minOut/got quantiles", q(first_ratio))
print("all bot buys", len(all_ratio), "minOut/got quantiles", q(all_ratio))
print("word3/got (first)", q(w3r))
for S, v in headroom.items():
    print(f"our buy {S/1e18:g} at the head: bot first buy output / its actual: quantiles {q([a for a, b, c in v])}; minOut/actual {q([b for a, b, c in v])}; "
          f"still >= minOut: {sum(1 for a, b, c in v if c)}/{len(v)}")
