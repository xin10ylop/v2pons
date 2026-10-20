#!/usr/bin/env python3
"""front_replay.py DEEP.json: the Robinhood engine's front rule replayed on the volume bot's current pools: fire at launch+0, land at +1 behind
that block's swaps; sell into the first bot-router buy behind ours (lands LAG blocks after it), or at take-profit 1%, or at our buy + 18;
the bot's buy reverts if our stake ahead pushes its output under minOut (0.95 x the launch quote); a pull at or before our sell = -100%."""
import json, os, sys, statistics as st, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src")); import v4math
BOT = "1cbaf24d53fe930fce8eff149fa797d2611da149"; BOT_MIN = 0.04e18; BOT_MINOUT = 0.95; TP = 0.01; HOLD = 18; GAS_USD = 0.02; ETH_USD = 2570.0
d = json.load(open(sys.argv[1])); P, E, T = d["pools"], d["events"], d["txs"]
def run(stake, lag):
    rows = []; reverts = 0; bot_buys = 0; triggers = collections.Counter(); pull_after = []
    for pid, p in P.items():
        e = E[pid]; L0 = p["bn"]; f = p["fee"] / 1e6; sw = sorted(e["swaps"]); pulls = [l[0] for l in e["liq"] if l[3] < 0]; pull = min(pulls) if pulls else None
        liq = e["liq"][0][3] if e["liq"] else 0
        if liq <= 0: continue
        def state(bn):
            prev = [s for s in sw if s[0] <= bn]; return (prev[-1][4], prev[-1][5]) if prev else (p["sqrtP0"], liq)
        buy_bn = L0 + 1; sp, L = state(buy_bn)
        if L == 0: continue
        x_net = int(stake * 1e18 * (1 - f)); tok = v4math.buy_out(sp, L, x_net)
        if tok <= 0: continue
        def ours(bn):
            s, l = state(bn); return (v4math.sqrt_after_buy(s, l, x_net) if l else s), l
        sell_bn = buy_bn + HOLD; trig = "deadline"
        for s in sw:
            if s[0] <= buy_bn: continue
            if s[0] >= sell_bn: break
            t = T.get(s[6]); val = -s[2] if s[2] < 0 else 0
            if t and t[1] == BOT and val >= BOT_MIN:
                bot_buys += 1
                sp_b, L_b = ours(s[0] - 1); quote = v4math.buy_out(p["sqrtP0"], liq, int(val * (1 - f))); actual = v4math.buy_out(sp_b, L_b, int(val * (1 - f)))
                if actual < BOT_MINOUT * quote: reverts += 1; continue
                sell_bn = s[0] + lag; trig = "bot"; break
            sp_o, L_o = ours(s[0])
            if L_o and v4math.sell_out(sp_o, L_o, int(tok * (1 - f))) >= stake * 1e18 * (1 + TP) + GAS_USD / ETH_USD * 1e18:
                sell_bn = s[0] + 1; trig = "tp"; break
        triggers[trig] += 1
        if pull is not None: pull_after.append(pull - buy_bn)
        if pull is not None and pull <= sell_bn: rows.append(-1.0); continue
        sp_s, L_s = ours(sell_bn)
        if L_s == 0: rows.append(-1.0); continue
        out = v4math.sell_out(sp_s, L_s, int(tok * (1 - f))); rows.append((out - stake * 1e18) / (stake * 1e18) - GAS_USD / (stake * ETH_USD))
    return rows, reverts, bot_buys, triggers, pull_after
print(f"{sys.argv[1]}: {len(P)} pools")
for stake in (0.0012, 0.005, 0.012, 0.03):
    for lag in (1, 2):
        rows, rev, nb, trig, pa = run(stake, lag)
        print(f"  stake {stake:<6} lag {lag}: n={len(rows)} mean {100*st.mean(rows):+.1f}% median {100*st.median(rows):+.1f}% win {100*sum(1 for r in rows if r > 0)/len(rows):.0f}% pulled {sum(1 for r in rows if r <= -0.99)}  triggers {dict(trig)}  bot buys seen {nb}, reverting under our stake {rev}")
rows, rev, nb, trig, pa = run(0.005, 1)
print("  pull minus our buy (blocks) p10/25/50/75/90:", [sorted(pa)[int(len(pa)*q)] for q in (0.1, 0.25, 0.5, 0.75, 0.9)] if pa else None, "; pulls within 18 blocks of our buy:", sum(1 for x in pa if x <= 18), "of", len(pa))
