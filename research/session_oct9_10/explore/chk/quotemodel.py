"""Which earlier buys does the volume bot's first-buy quote include? Implied net ETH bought before its quote = (1/s_q - 1/s_0) L, from
minOut = 0.99 x buy_out(s_q, L, X); compare with the earlier swaps by sender."""
import pickle, sys, collections
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb")); TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
Q = 2 ** 96; FEE = 2500
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
def net(x): return x - (x * FEE + 999999) // 1000000
match = collections.Counter(); ex = []
for p in fam:
    L = p["sw"][0][5]; s0 = p["sp0"] / Q
    pre = []
    for x in p["sw"]:
        t = TX.get(x[7])
        if t and t["sel"] == "0xc1120e3d" and x[2] < 0:
            mo = wd(t["input"], 4); X = t["value"]; xn = net(X)
            q = mo / 0.99
            # buy_out = L (s_q - s_after), s_after = 1/(1/s_q + xn/L): solve for s_q numerically
            lo, hi = s0 * 0.5, s0 * 1.0000001
            for _ in range(200):
                m = (lo + hi) / 2; o = L * (m - 1 / (1 / m + xn / L))
                if o > q: hi = m
                else: lo = m
            implied = (1 / lo - 1 / s0) * L / 1e18
            by = collections.defaultdict(float)
            for (rel, eth, who) in pre: by[who] += eth
            # subsets of senders
            ws = list(by)
            best = None
            for mask in range(1 << len(ws)):
                sub = [ws[i] for i in range(len(ws)) if mask >> i & 1]
                tot = sum(by[w] * (1 - FEE / 1e6) for w in sub)
                err = abs(tot - implied)
                if best is None or err < best[0]: best = (err, tuple(sorted(sub)), tot)
            key = best[1] if best[0] < max(2e-8, 0.002 * implied) else ("nomatch",)
            match[key] += 1
            if len(ex) < 8: ex.append((p["pid"][:10], x[0] - p["b0"], round(implied, 9), [(r, round(e, 7), w) for r, e, w in pre], key))
            break
        tt = TX.get(x[7])
        if x[2] < 0: pre.append((x[0] - p["b0"], -x[2] / 1e18, (tt["to"][:10] + ":" + tt["from"][:8]) if tt else "?"))
        else: pre.append((x[0] - p["b0"], -x[2] / 1e18, "SELL"))
for k, v in match.most_common(15): print(v, k)
for e in ex: print(e)
